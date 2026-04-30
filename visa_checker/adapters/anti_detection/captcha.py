"""CAPTCHA solver adapters (2captcha, AntiCaptcha, no-op)."""
from __future__ import annotations

import asyncio
from typing import Any

import httpx

from visa_checker.domain.errors import CaptchaError
from visa_checker.ports.captcha import ICaptchaSolver

_POLL_INTERVAL = 5
_MAX_WAIT = 120


async def _poll_result(client: httpx.AsyncClient, url: str, max_wait: int) -> str:
    for _ in range(max_wait // _POLL_INTERVAL):
        await asyncio.sleep(_POLL_INTERVAL)
        resp = await client.get(url)
        data = resp.text
        if "CAPCHA_NOT_READY" in data or "NOT_READY" in data:
            continue
        if data.startswith("OK|"):
            return data.split("|", 1)[1]
        raise CaptchaError(f"Unexpected solver response: {data}")
    raise CaptchaError("CAPTCHA solving timed out")


class NullCaptchaSolver(ICaptchaSolver):
    """Raises immediately — surfaces misconfiguration clearly."""

    async def solve(self, page: Any) -> str:
        raise CaptchaError(
            "CAPTCHA detected but no solver is configured. "
            "Set captcha.provider to '2captcha' or 'anticaptcha' in config.yaml."
        )


class TwoCaptchaSolver(ICaptchaSolver):
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def _get_sitekey(self, page: Any) -> tuple[str, str]:
        """Return (type, sitekey). type is 'recaptcha' or 'hcaptcha'."""
        sitekey = await page.evaluate(
            """() => {
                const rc = document.querySelector('[data-sitekey]');
                if (rc) return JSON.stringify({type: 'recaptcha', key: rc.dataset.sitekey});
                const hc = document.querySelector('[data-hcaptcha-sitekey]');
                if (hc) return JSON.stringify({type: 'hcaptcha', key: hc.dataset.hcaptchaSitekey});
                return null;
            }"""
        )
        if not sitekey:
            raise CaptchaError("No CAPTCHA found on page")
        import json
        data = json.loads(sitekey)
        return data["type"], data["key"]

    async def solve(self, page: Any) -> str:
        captcha_type, sitekey = await self._get_sitekey(page)
        page_url = page.url

        async with httpx.AsyncClient(timeout=30) as client:
            if captcha_type == "recaptcha":
                resp = await client.post(
                    "http://2captcha.com/in.php",
                    data={
                        "key": self._api_key,
                        "method": "userrecaptcha",
                        "googlekey": sitekey,
                        "pageurl": page_url,
                        "json": 1,
                    },
                )
            else:
                resp = await client.post(
                    "http://2captcha.com/in.php",
                    data={
                        "key": self._api_key,
                        "method": "hcaptcha",
                        "sitekey": sitekey,
                        "pageurl": page_url,
                        "json": 1,
                    },
                )
            result = resp.json()
            if result.get("status") != 1:
                raise CaptchaError(f"2captcha submission failed: {result}")
            task_id = result["request"]

            token = await _poll_result(
                client,
                f"http://2captcha.com/res.php?key={self._api_key}&action=get&id={task_id}",
                _MAX_WAIT,
            )

        # Inject token
        if captcha_type == "recaptcha":
            await page.evaluate(
                f'document.getElementById("g-recaptcha-response").innerHTML = "{token}";'
            )
        else:
            await page.evaluate(
                f'document.querySelector("[name=h-captcha-response]").value = "{token}";'
            )
        return token


class AntiCaptchaSolver(ICaptchaSolver):
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def solve(self, page: Any) -> str:
        # AntiCaptcha uses a different API endpoint but same flow
        raise NotImplementedError("AntiCaptcha integration coming soon")


def build_captcha_solver(config: object) -> ICaptchaSolver:
    """Factory that builds the correct CAPTCHA solver from config."""
    from visa_checker.config.settings import CaptchaConfig

    cfg: CaptchaConfig = config  # type: ignore[assignment]
    if cfg.provider == "2captcha":
        return TwoCaptchaSolver(cfg.api_key)
    if cfg.provider == "anticaptcha":
        return AntiCaptchaSolver(cfg.api_key)
    return NullCaptchaSolver()
