"""CAPTCHA solver adapters.

Free options (no API key required):
  audio_recaptcha         — reCAPTCHA v2 audio challenge solved via Google speech-to-text
  hcaptcha_accessibility  — hCaptcha accessibility cookie bypass (register once at hcaptcha.com)
  manual                  — pause + send Telegram screenshot, wait for human to solve

Paid options:
  2captcha / anticaptcha  — human workers, ~$2/1000 solves

Default: audio_recaptcha (covers VFS Global login reCAPTCHA v2).
For TLScontact (hCaptcha) use hcaptcha_accessibility or manual.

Provider CAPTCHA map:
  VFS Global       → reCAPTCHA v2  (on login page only, skipped when session is warm)
  TLScontact       → hCaptcha      (on login page only)
  BLS / Capago     → varies        (sometimes absent entirely)
  Cloudflare pages → Turnstile     (cf-turnstile, detected but not solvable automatically)
"""
from __future__ import annotations

import asyncio
import json as _json
from typing import Any

import httpx
from loguru import logger

from visa_checker.domain.errors import CaptchaError
from visa_checker.ports.captcha import ICaptchaSolver

_POLL_INTERVAL = 5
_MAX_WAIT = 120
_AUDIO_MAX_RETRIES = 3


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _detect_captcha_type(page: Any) -> tuple[str, str] | None:
    """Return ('recaptcha'|'hcaptcha'|'turnstile', sitekey) or None.

    hCaptcha is checked BEFORE the generic [data-sitekey] selector because
    hCaptcha also sets data-sitekey on its widget elements — the generic
    selector would mis-label hCaptcha as reCAPTCHA.
    """
    result = await page.evaluate(
        """() => {
            // 1. Cloudflare Turnstile
            const cf = document.querySelector('.cf-turnstile, [data-cf-turnstile]');
            if (cf) {
                const key = cf.dataset.sitekey || cf.dataset.cfTurnstile || '';
                return JSON.stringify({type: 'turnstile', key});
            }

            // 2. hCaptcha — checked before generic data-sitekey
            const hc = document.querySelector(
                '.h-captcha, [data-hcaptcha-sitekey], iframe[src*="hcaptcha.com"]'
            );
            if (hc) {
                const key = hc.dataset.hcaptchaSitekey
                         || hc.dataset.sitekey
                         || '';
                return JSON.stringify({type: 'hcaptcha', key});
            }

            // 3. reCAPTCHA v2 / v3
            const rc = document.querySelector(
                '.g-recaptcha, [data-sitekey]:not(.h-captcha), iframe[src*="recaptcha.net"], iframe[src*="google.com/recaptcha"]'
            );
            if (rc) {
                return JSON.stringify({type: 'recaptcha', key: rc.dataset.sitekey || ''});
            }

            return null;
        }"""
    )
    if not result:
        return None
    data = _json.loads(result)
    return data["type"], data["key"]


async def _poll_2captcha(client: httpx.AsyncClient, url: str) -> str:
    for _ in range(_MAX_WAIT // _POLL_INTERVAL):
        await asyncio.sleep(_POLL_INTERVAL)
        resp = await client.get(url)
        data = resp.text
        if "NOT_READY" in data or "CAPCHA_NOT_READY" in data:
            continue
        if data.startswith("OK|"):
            return data.split("|", 1)[1]
        raise CaptchaError(f"2captcha unexpected response: {data}")
    raise CaptchaError("2captcha timed out after {}s".format(_MAX_WAIT))


async def _inject_recaptcha_token(page: Any, token: str) -> None:
    """Inject a solved reCAPTCHA v2 token and fire the widget callback."""
    await page.evaluate(
        """(token) => {
            // Fill the hidden textarea
            const ta = document.getElementById('g-recaptcha-response');
            if (ta) { ta.innerHTML = token; }

            // Fire the widget's onSuccess callback so the form unlocks
            try {
                const clients = window.___grecaptcha_cfg && window.___grecaptcha_cfg.clients;
                if (clients) {
                    for (const id of Object.keys(clients)) {
                        const client = clients[id];
                        for (const key of Object.keys(client)) {
                            const field = client[key];
                            if (field && typeof field === 'object' && field.callback) {
                                field.callback(token);
                                return;
                            }
                        }
                    }
                }
            } catch (_) {}
        }""",
        token,  # passed as argument — not baked into the JS string
    )


async def _inject_hcaptcha_token(page: Any, token: str) -> None:
    """Inject a solved hCaptcha token and fire the submit callback."""
    await page.evaluate(
        """(token) => {
            const ta = document.querySelector('[name="h-captcha-response"]');
            if (ta) { ta.value = token; }
            // Attempt to fire the hcaptcha callback
            try {
                const widget = window.hcaptcha;
                if (widget && widget.execute) { widget.execute(); }
            } catch (_) {}
        }""",
        token,
    )


# ---------------------------------------------------------------------------
# Free solver 1: Audio reCAPTCHA (no API key, uses Google speech-to-text)
# ---------------------------------------------------------------------------

class AudioReCaptchaSolver(ICaptchaSolver):
    """Solves reCAPTCHA v2 by clicking the audio challenge and transcribing it.

    Requires: uv add playwright-recaptcha
    Requires: ffmpeg installed (winget install ffmpeg / apt install ffmpeg)

    Works for: VFS Global (reCAPTCHA v2)
    Raises CaptchaError for hCaptcha — use HCaptchaAccessibilitySolver for TLScontact.

    Retries up to _AUDIO_MAX_RETRIES times because Google's STT rejects ~20%
    of audio challenges due to audio quality.
    """

    async def solve(self, page: Any) -> str:
        captcha = await _detect_captcha_type(page)
        if captcha is None:
            return ""

        captcha_type, _ = captcha

        if captcha_type == "turnstile":
            raise CaptchaError(
                "Cloudflare Turnstile detected — this is a browser challenge, not a CAPTCHA. "
                "The stealth browser should pass it automatically. If it doesn't, try a different proxy."
            )

        if captcha_type == "hcaptcha":
            raise CaptchaError(
                "hCaptcha detected on this page. AudioReCaptchaSolver only handles reCAPTCHA v2. "
                "Switch captcha.provider to 'hcaptcha_accessibility' or 'manual'."
            )

        try:
            from playwright_recaptcha import recaptchav2
        except ImportError:
            raise CaptchaError(
                "playwright-recaptcha not installed. Run: uv add playwright-recaptcha\n"
                "Also requires ffmpeg: winget install ffmpeg (Windows) / apt install ffmpeg (Linux)"
            )

        last_exc: Exception | None = None
        for attempt in range(1, _AUDIO_MAX_RETRIES + 1):
            try:
                logger.info("[captcha] Solving reCAPTCHA v2 via audio (attempt {}/{})", attempt, _AUDIO_MAX_RETRIES)
                async with recaptchav2.AsyncSolver(page) as solver:
                    token = await solver.solve_recaptcha(wait=True)
                logger.info("[captcha] reCAPTCHA v2 solved")
                return token
            except Exception as exc:
                last_exc = exc
                if attempt < _AUDIO_MAX_RETRIES:
                    logger.warning("[captcha] Audio solve failed (attempt {}): {} — retrying", attempt, exc)
                    await asyncio.sleep(2)

        raise CaptchaError(f"Audio reCAPTCHA failed after {_AUDIO_MAX_RETRIES} attempts: {last_exc}") from last_exc


# ---------------------------------------------------------------------------
# Free solver 2: hCaptcha accessibility cookie bypass
# ---------------------------------------------------------------------------

class HCaptchaAccessibilitySolver(ICaptchaSolver):
    """Bypasses hCaptcha using hCaptcha's official accessibility token cookie.

    How to get a free token (takes ~2 minutes, valid for ~1 year):
      1. Visit https://www.hcaptcha.com/accessibility
      2. Enter your email — they send a magic link
      3. Click the link — your browser sets an `hc_accessibility` cookie
      4. Copy that cookie value into your .env: HCAPTCHA_ACCESSIBILITY_TOKEN=...

    Works for: TLScontact (hCaptcha)
    Falls back to AudioReCaptchaSolver for reCAPTCHA pages.

    The cookie is injected BEFORE navigating to the login page so hCaptcha's
    JS sees it on first load — no page reload required.
    """

    def __init__(self, accessibility_token: str, recaptcha_fallback: ICaptchaSolver | None = None) -> None:
        self._token = accessibility_token
        self._fallback = recaptcha_fallback or AudioReCaptchaSolver()

    async def _inject_cookie(self, page: Any) -> None:
        """Inject the hc_accessibility cookie into the browser context."""
        await page.context.add_cookies([
            {
                "name": "hc_accessibility",
                "value": self._token,
                "domain": ".hcaptcha.com",
                "path": "/",
                "secure": True,
                "httpOnly": False,
                "sameSite": "None",
            }
        ])

    async def pre_navigate(self, page: Any) -> None:
        """Call this BEFORE navigating to the login page for best results."""
        if self._token:
            await self._inject_cookie(page)

    async def solve(self, page: Any) -> str:
        captcha = await _detect_captcha_type(page)
        if captcha is None:
            return ""

        captcha_type, _ = captcha

        if captcha_type == "recaptcha":
            logger.info("[captcha] reCAPTCHA detected — delegating to audio fallback")
            return await self._fallback.solve(page)

        if captcha_type == "turnstile":
            raise CaptchaError("Cloudflare Turnstile detected — change proxy and retry.")

        if not self._token:
            raise CaptchaError(
                "hCaptcha accessibility token is not set. "
                "Register at https://www.hcaptcha.com/accessibility and set "
                "HCAPTCHA_ACCESSIBILITY_TOKEN in your .env file."
            )

        # If we're here, the cookie wasn't injected before page load.
        # Inject now and reload — hCaptcha will read it on reinitialisation.
        logger.info("[captcha] Injecting hCaptcha accessibility cookie and reloading…")
        await self._inject_cookie(page)
        await page.reload(wait_until="networkidle", timeout=20000)
        await asyncio.sleep(1.5)

        captcha_after = await _detect_captcha_type(page)
        if captcha_after is not None and captcha_after[0] == "hcaptcha":
            raise CaptchaError(
                "hCaptcha accessibility token did not bypass the challenge. "
                "The token may be expired — get a new one at https://www.hcaptcha.com/accessibility"
            )

        logger.info("[captcha] hCaptcha bypassed via accessibility token")
        return "accessibility_bypass"


# ---------------------------------------------------------------------------
# Free solver 3: Manual — pause, send screenshot, wait for human
# ---------------------------------------------------------------------------

class ManualCaptchaSolver(ICaptchaSolver):
    """Pauses, sends a Telegram screenshot, and waits for the user to solve it manually.

    Requires headed browser (set headless: false in your browser config).
    The scraper resumes automatically once the CAPTCHA disappears from the page.
    Times out after `timeout_seconds` and raises CaptchaError.
    """

    def __init__(self, bot_token: str = "", chat_id: str = "", timeout_seconds: int = 300) -> None:
        self._bot_token = bot_token
        self._chat_id = chat_id
        self._timeout = timeout_seconds

    async def _send_telegram_screenshot(self, page: Any) -> None:
        if not self._bot_token or not self._chat_id:
            logger.warning("[captcha] No Telegram credentials — skipping screenshot notification")
            return
        try:
            screenshot = await page.screenshot(type="png")
            url = f"https://api.telegram.org/bot{self._bot_token}/sendPhoto"
            async with httpx.AsyncClient(timeout=15) as client:
                await client.post(
                    url,
                    data={
                        "chat_id": self._chat_id,
                        "caption": (
                            "⚠️ CAPTCHA detected — please solve it in the browser window. "
                            f"I will continue automatically (timeout: {self._timeout}s)."
                        ),
                    },
                    files={"photo": ("captcha.png", screenshot, "image/png")},
                )
            logger.info("[captcha] Screenshot sent to Telegram. Waiting up to {}s.", self._timeout)
        except Exception as exc:
            logger.warning("[captcha] Failed to send screenshot: {}", exc)

    async def solve(self, page: Any) -> str:
        captcha = await _detect_captcha_type(page)
        if captcha is None:
            return ""

        logger.info("[captcha] Manual solve required ({} type detected)", captcha[0])
        await self._send_telegram_screenshot(page)

        loop = asyncio.get_running_loop()
        deadline = loop.time() + self._timeout

        while loop.time() < deadline:
            await asyncio.sleep(3)
            if await _detect_captcha_type(page) is None:
                logger.info("[captcha] CAPTCHA resolved — continuing")
                return "manual_solve"

        raise CaptchaError(
            f"Manual CAPTCHA solve timed out after {self._timeout}s. "
            "Restart the scraper to try again."
        )


# ---------------------------------------------------------------------------
# Paid solver: 2captcha
# ---------------------------------------------------------------------------

class TwoCaptchaSolver(ICaptchaSolver):
    """Human-worker solving via 2captcha (~$2/1000 solves). Handles both reCAPTCHA v2 and hCaptcha."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def solve(self, page: Any) -> str:
        captcha = await _detect_captcha_type(page)
        if captcha is None:
            return ""

        captcha_type, sitekey = captcha
        if captcha_type == "turnstile":
            raise CaptchaError("Cloudflare Turnstile is not supported by 2captcha in this integration.")

        page_url = page.url

        async with httpx.AsyncClient(timeout=30, base_url="https://2captcha.com") as client:
            if captcha_type == "recaptcha":
                resp = await client.post("/in.php", data={
                    "key": self._api_key, "method": "userrecaptcha",
                    "googlekey": sitekey, "pageurl": page_url, "json": 1,
                })
            else:
                resp = await client.post("/in.php", data={
                    "key": self._api_key, "method": "hcaptcha",
                    "sitekey": sitekey, "pageurl": page_url, "json": 1,
                })

            result = resp.json()
            if result.get("status") != 1:
                raise CaptchaError(f"2captcha submission failed: {result}")

            token = await _poll_2captcha(
                client, f"/res.php?key={self._api_key}&action=get&id={result['request']}"
            )

        if captcha_type == "recaptcha":
            await _inject_recaptcha_token(page, token)
        else:
            await _inject_hcaptcha_token(page, token)

        logger.info("[captcha] 2captcha solved {} CAPTCHA", captcha_type)
        return token


# ---------------------------------------------------------------------------
# Paid solver: AntiCaptcha
# ---------------------------------------------------------------------------

class AntiCaptchaSolver(ICaptchaSolver):
    """Human-worker solving via anti-captcha.com (~$2/1000 solves). Handles reCAPTCHA v2 and hCaptcha."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def _create_task(self, client: httpx.AsyncClient, task: dict) -> str:
        resp = await client.post("/createTask", json={"clientKey": self._api_key, "task": task})
        data = resp.json()
        if data.get("errorId", 0) != 0:
            raise CaptchaError(f"AntiCaptcha createTask failed: {data.get('errorDescription')}")
        return str(data["taskId"])

    async def _get_result(self, client: httpx.AsyncClient, task_id: str) -> str:
        for _ in range(_MAX_WAIT // _POLL_INTERVAL):
            await asyncio.sleep(_POLL_INTERVAL)
            resp = await client.post("/getTaskResult", json={"clientKey": self._api_key, "taskId": task_id})
            data = resp.json()
            if data.get("errorId", 0) != 0:
                raise CaptchaError(f"AntiCaptcha error: {data.get('errorDescription')}")
            if data.get("status") == "ready":
                return data["solution"]["gRecaptchaResponse"]
        raise CaptchaError("AntiCaptcha timed out")

    async def solve(self, page: Any) -> str:
        captcha = await _detect_captcha_type(page)
        if captcha is None:
            return ""

        captcha_type, sitekey = captcha
        if captcha_type == "turnstile":
            raise CaptchaError("Cloudflare Turnstile not supported by AntiCaptcha in this integration.")

        async with httpx.AsyncClient(timeout=30, base_url="https://api.anti-captcha.com") as client:
            if captcha_type == "recaptcha":
                task = {"type": "NoCaptchaTaskProxyless", "websiteURL": page.url, "websiteKey": sitekey}
            else:
                task = {"type": "HCaptchaTaskProxyless", "websiteURL": page.url, "websiteKey": sitekey}

            task_id = await self._create_task(client, task)
            token = await self._get_result(client, task_id)

        if captcha_type == "recaptcha":
            await _inject_recaptcha_token(page, token)
        else:
            await _inject_hcaptcha_token(page, token)

        logger.info("[captcha] AntiCaptcha solved {} CAPTCHA", captcha_type)
        return token


# ---------------------------------------------------------------------------
# No-op
# ---------------------------------------------------------------------------

class NullCaptchaSolver(ICaptchaSolver):
    async def solve(self, page: Any) -> str:
        captcha = await _detect_captcha_type(page)
        if captcha is None:
            return ""
        raise CaptchaError(
            f"{captcha[0]} CAPTCHA detected but no solver is configured. "
            "Set captcha.provider to 'audio_recaptcha' (free, works for VFS Global) "
            "or 'hcaptcha_accessibility' (free, works for TLScontact) in config.yaml."
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def build_captcha_solver(config: object) -> ICaptchaSolver:
    from visa_checker.config.settings import CaptchaConfig

    cfg: CaptchaConfig = config  # type: ignore[assignment]

    if cfg.provider == "audio_recaptcha":
        return AudioReCaptchaSolver()

    if cfg.provider == "hcaptcha_accessibility":
        return HCaptchaAccessibilitySolver(
            accessibility_token=cfg.hcaptcha_accessibility_token,
            recaptcha_fallback=AudioReCaptchaSolver(),
        )

    if cfg.provider == "manual":
        return ManualCaptchaSolver(
            bot_token=cfg.manual_telegram_bot_token,
            chat_id=cfg.manual_telegram_chat_id,
        )

    if cfg.provider == "2captcha":
        return TwoCaptchaSolver(cfg.api_key)

    if cfg.provider == "anticaptcha":
        return AntiCaptchaSolver(cfg.api_key)

    return NullCaptchaSolver()
