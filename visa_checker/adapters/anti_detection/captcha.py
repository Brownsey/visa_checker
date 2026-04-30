"""CAPTCHA solver adapters.

Free options (no API key required):
  audio_recaptcha         — reCAPTCHA v2 audio challenge solved via Google speech-to-text
  hcaptcha_accessibility  — hCaptcha accessibility cookie bypass (register once at hcaptcha.com)
  manual                  — pause + send Telegram screenshot, wait for human to solve

Paid options:
  2captcha / anticaptcha  — human workers, ~$2/1000 solves

Default: audio_recaptcha (covers VFS Global). For TLScontact (hCaptcha), use
hcaptcha_accessibility or pair audio_recaptcha as fallback.
"""
from __future__ import annotations

import asyncio
import io
import tempfile
from pathlib import Path
from typing import Any

import httpx
from loguru import logger

from visa_checker.domain.errors import CaptchaError
from visa_checker.ports.captcha import ICaptchaSolver

_POLL_INTERVAL = 5
_MAX_WAIT = 120


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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
    raise CaptchaError("2captcha timed out")


async def _detect_captcha_type(page: Any) -> tuple[str, str] | None:
    """Return ('recaptcha'|'hcaptcha', sitekey) or None if no CAPTCHA found."""
    import json
    result = await page.evaluate(
        """() => {
            const rc = document.querySelector('[data-sitekey]');
            if (rc) return JSON.stringify({type: 'recaptcha', key: rc.dataset.sitekey});
            const hc = document.querySelector('[data-hcaptcha-sitekey], .h-captcha[data-sitekey]');
            if (hc) {
                const key = hc.dataset.hcaptchaSitekey || hc.dataset.sitekey;
                return JSON.stringify({type: 'hcaptcha', key});
            }
            return null;
        }"""
    )
    if not result:
        return None
    data = json.loads(result)
    return data["type"], data["key"]


# ---------------------------------------------------------------------------
# Free solver 1: Audio reCAPTCHA (no API key, uses Google speech-to-text)
# ---------------------------------------------------------------------------

class AudioReCaptchaSolver(ICaptchaSolver):
    """Solves reCAPTCHA v2 by clicking the audio challenge and transcribing it.

    Requires: uv add playwright-recaptcha
    Requires: ffmpeg installed on the system (winget install ffmpeg / apt install ffmpeg)

    Works for: VFS Global (reCAPTCHA v2)
    Does NOT handle hCaptcha — falls back to NullCaptchaSolver for those.
    """

    async def solve(self, page: Any) -> str:
        captcha = await _detect_captcha_type(page)
        if captcha is None:
            logger.debug("[captcha] No CAPTCHA detected on page")
            return ""

        captcha_type, _ = captcha

        if captcha_type == "hcaptcha":
            raise CaptchaError(
                "AudioReCaptchaSolver cannot solve hCaptcha. "
                "Switch to 'hcaptcha_accessibility' or 'manual' in captcha.provider."
            )

        try:
            from playwright_recaptcha import recaptchav2
        except ImportError:
            raise CaptchaError(
                "playwright-recaptcha is not installed. Run: uv add playwright-recaptcha\n"
                "Also ensure ffmpeg is installed: winget install ffmpeg"
            )

        logger.info("[captcha] Solving reCAPTCHA v2 via audio challenge…")
        try:
            async with recaptchav2.AsyncSolver(page) as solver:
                token = await solver.solve_recaptcha(wait=True)
            logger.info("[captcha] reCAPTCHA v2 solved via audio")
            return token
        except Exception as exc:
            raise CaptchaError(f"Audio reCAPTCHA solving failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Free solver 2: hCaptcha accessibility cookie bypass
# ---------------------------------------------------------------------------

class HCaptchaAccessibilitySolver(ICaptchaSolver):
    """Bypasses hCaptcha using the official accessibility token cookie.

    How to get a free token:
      1. Visit https://www.hcaptcha.com/accessibility
      2. Enter your email, they send you a link
      3. Click the link — you get an hc_accessibility cookie value
      4. Put that value in config.yaml: captcha.hcaptcha_accessibility_token
      5. The token is valid for ~1 year

    Works for: TLScontact (hCaptcha)
    Falls back to audio solver for reCAPTCHA.
    """

    def __init__(self, accessibility_token: str, recaptcha_fallback: ICaptchaSolver | None = None) -> None:
        self._token = accessibility_token
        self._fallback = recaptcha_fallback or AudioReCaptchaSolver()

    async def solve(self, page: Any) -> str:
        captcha = await _detect_captcha_type(page)
        if captcha is None:
            return ""

        captcha_type, _ = captcha

        if captcha_type == "recaptcha":
            logger.info("[captcha] reCAPTCHA detected — using audio fallback")
            return await self._fallback.solve(page)

        if not self._token:
            raise CaptchaError(
                "hCaptcha accessibility token not configured. "
                "Register at https://www.hcaptcha.com/accessibility and set "
                "captcha.hcaptcha_accessibility_token in config.yaml."
            )

        logger.info("[captcha] Injecting hCaptcha accessibility cookie…")

        # Set the accessibility cookie before any hCaptcha JS runs
        await page.context.add_cookies([
            {
                "name": "hc_accessibility",
                "value": self._token,
                "domain": ".hcaptcha.com",
                "path": "/",
                "secure": True,
                "httpOnly": False,
            }
        ])

        # Reload the page so hCaptcha sees the cookie on initialisation
        await page.reload(wait_until="networkidle", timeout=20000)

        # Verify the CAPTCHA is gone
        await asyncio.sleep(1.5)
        captcha_after = await _detect_captcha_type(page)
        if captcha_after is not None:
            raise CaptchaError(
                "hCaptcha accessibility token did not bypass the challenge. "
                "Token may be expired — get a new one at https://www.hcaptcha.com/accessibility"
            )

        logger.info("[captcha] hCaptcha bypassed via accessibility token")
        return "accessibility_bypass"


# ---------------------------------------------------------------------------
# Free solver 3: Manual — pause, send screenshot, wait for human
# ---------------------------------------------------------------------------

class ManualCaptchaSolver(ICaptchaSolver):
    """Pauses the scraper, sends a screenshot to Telegram, and waits for you to solve it.

    The page stays open (headed browser recommended for this solver).
    Once you solve the CAPTCHA in the browser window and press Enter in the
    Telegram-connected chat (or wait the timeout), the scraper continues.

    Set headless: false in your config when using this solver.
    """

    def __init__(
        self,
        bot_token: str = "",
        chat_id: str = "",
        timeout_seconds: int = 300,
    ) -> None:
        self._bot_token = bot_token
        self._chat_id = chat_id
        self._timeout = timeout_seconds

    async def _send_telegram_screenshot(self, page: Any) -> None:
        if not self._bot_token or not self._chat_id:
            logger.warning("[captcha] No Telegram credentials for manual solver — skipping screenshot")
            return
        try:
            screenshot = await page.screenshot(type="png")
            url = f"https://api.telegram.org/bot{self._bot_token}/sendPhoto"
            async with httpx.AsyncClient(timeout=15) as client:
                await client.post(
                    url,
                    data={"chat_id": self._chat_id, "caption": "⚠️ CAPTCHA detected! Please solve it in the browser and I'll continue automatically."},
                    files={"photo": ("captcha.png", screenshot, "image/png")},
                )
            logger.info("[captcha] Screenshot sent to Telegram — waiting {}s for manual solve", self._timeout)
        except Exception as exc:
            logger.warning("[captcha] Failed to send Telegram screenshot: {}", exc)

    async def solve(self, page: Any) -> str:
        captcha = await _detect_captcha_type(page)
        if captcha is None:
            return ""

        await self._send_telegram_screenshot(page)

        # Poll until the CAPTCHA disappears (user solved it) or timeout
        deadline = asyncio.get_event_loop().time() + self._timeout
        while asyncio.get_event_loop().time() < deadline:
            await asyncio.sleep(3)
            remaining = await _detect_captcha_type(page)
            if remaining is None:
                logger.info("[captcha] CAPTCHA appears solved — continuing")
                return "manual_solve"

        raise CaptchaError(
            f"Manual CAPTCHA solve timed out after {self._timeout}s. "
            "Restart the scraper to try again."
        )


# ---------------------------------------------------------------------------
# Paid solver: 2captcha
# ---------------------------------------------------------------------------

class TwoCaptchaSolver(ICaptchaSolver):
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def solve(self, page: Any) -> str:
        captcha = await _detect_captcha_type(page)
        if captcha is None:
            return ""
        captcha_type, sitekey = captcha
        page_url = page.url

        async with httpx.AsyncClient(timeout=30) as client:
            method = "userrecaptcha" if captcha_type == "recaptcha" else "hcaptcha"
            key_field = "googlekey" if captcha_type == "recaptcha" else "sitekey"
            resp = await client.post(
                "http://2captcha.com/in.php",
                data={"key": self._api_key, "method": method, key_field: sitekey, "pageurl": page_url, "json": 1},
            )
            result = resp.json()
            if result.get("status") != 1:
                raise CaptchaError(f"2captcha submission failed: {result}")
            token = await _poll_2captcha(
                client, f"http://2captcha.com/res.php?key={self._api_key}&action=get&id={result['request']}"
            )

        field = "g-recaptcha-response" if captcha_type == "recaptcha" else "[name=h-captcha-response]"
        if captcha_type == "recaptcha":
            await page.evaluate(f'document.getElementById("{field}").innerHTML = "{token}";')
        else:
            await page.evaluate(f'document.querySelector("{field}").value = "{token}";')
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
            "CAPTCHA detected but no solver is configured. "
            "Set captcha.provider to 'audio_recaptcha' (free) in config.yaml."
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

    return NullCaptchaSolver()
