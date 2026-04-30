"""TLScontact scraper — France, Portugal, Belgium, Denmark, Netherlands."""
from __future__ import annotations

import json
from datetime import date
from typing import Any

from loguru import logger

from visa_checker.adapters.browser.human import BehaviourConfig, human_click, human_type, random_mouse_movement
from visa_checker.adapters.scrapers.base import BaseScraper, register_scraper
from visa_checker.adapters.scrapers.vfs_global import _parse_date
from visa_checker.config.settings import TargetConfig
from visa_checker.domain.errors import AuthError, BlockedError
from visa_checker.domain.models import SlotResult
from visa_checker.ports.browser import IBrowserEngine
from visa_checker.ports.captcha import ICaptchaSolver

_COUNTRY_SUBDOMAINS: dict[str, str] = {
    "france": "fr",
    "portugal": "pt",
    "belgium": "be",
    "denmark": "dk",
    "netherlands": "nl",
    "luxembourg": "lu",
}

_CENTRE_CODES: dict[str, str] = {
    "london": "lon",
    "edinburgh": "edi",
    "manchester": "man",
}


@register_scraper("tlscontact")
class TLSContactScraper(BaseScraper):
    def __init__(
        self,
        target: TargetConfig,
        browser: IBrowserEngine,
        email: str,
        password: str,
        captcha_solver: ICaptchaSolver | None = None,
        behaviour: BehaviourConfig | None = None,
    ) -> None:
        self._target = target
        self._browser = browser
        self._email = email
        self._password = password
        self._captcha_solver = captcha_solver
        self._behaviour = behaviour
        self._page: Any = None
        self._captured_slots: list[SlotResult] = []

    @property
    def provider_name(self) -> str:
        return "tlscontact"

    def _subdomain(self) -> str:
        return _COUNTRY_SUBDOMAINS.get(self._target.country.lower(), "fr")

    def _centre_code(self) -> str:
        return _CENTRE_CODES.get(self._target.centre.lower(), "lon")

    def _base_url(self) -> str:
        return f"https://{self._subdomain()}.tlscontact.com/gb/{self._centre_code()}"

    async def _get_page(self) -> Any:
        if self._page is None or self._page.is_closed():
            self._page = await self._browser.new_page()
        return self._page

    async def is_logged_in(self) -> bool:
        try:
            page = await self._get_page()
            await page.goto(self._base_url() + "/appointment", wait_until="domcontentloaded", timeout=15000)
            return "login" not in page.url and "signin" not in page.url
        except Exception:
            return False

    async def login(self) -> None:
        page = await self._get_page()
        await random_mouse_movement(page, cfg=self._behaviour)

        # Pre-inject hCaptcha accessibility cookie BEFORE loading the login page
        # so hCaptcha's JS sees it on first initialisation (no reload needed)
        if self._captcha_solver and hasattr(self._captcha_solver, "pre_navigate"):
            await self._captcha_solver.pre_navigate(page)

        login_url = self._base_url() + "/login"
        logger.info("[tlscontact] Navigating to login: {}", login_url)
        await page.goto(login_url, wait_until="networkidle", timeout=30000)

        content = await page.content()
        if "cloudflare" in content.lower():
            raise BlockedError("TLScontact is behind Cloudflare — IP may be blocked")

        await human_type(page, "input[type=email], input[name=email]", self._email, cfg=self._behaviour)
        await human_type(page, "input[type=password], input[name=password]", self._password, cfg=self._behaviour)

        # Solve CAPTCHA unconditionally — solver returns "" if none is present.
        # HCaptchaAccessibilitySolver injects its cookie before navigation via pre_navigate();
        # by the time we reach here the challenge should already be bypassed.
        if self._captcha_solver:
            await self._captcha_solver.solve(page)

        await human_click(page, "button[type=submit], input[type=submit]", cfg=self._behaviour)
        await page.wait_for_load_state("networkidle", timeout=20000)

        if "login" in page.url or "signin" in page.url:
            raise AuthError("TLScontact login failed — check credentials")

        logger.info("[tlscontact] Login successful")

    async def check_slots(self) -> list[SlotResult]:
        page = await self._get_page()
        self._captured_slots = []

        # Intercept AJAX calendar responses
        async def _on_response(response: Any) -> None:
            try:
                url = response.url
                if "appointment" in url and "available" in url:
                    body = await response.json()
                    self._captured_slots.extend(_parse_tls_calendar(body, self._target))
            except Exception:
                pass

        page.on("response", _on_response)

        appointment_url = self._base_url() + "/appointment"
        logger.info("[tlscontact] Checking slots at {}", appointment_url)
        await page.goto(appointment_url, wait_until="networkidle", timeout=30000)

        content = await page.content()
        if "no appointment" in content.lower() or "no slot" in content.lower():
            return []

        # Also try parsing the rendered calendar DOM
        dom_slots = await _parse_calendar_dom(page, self._target, self._base_url())
        all_slots = self._captured_slots + dom_slots

        page.remove_listener("response", _on_response)
        logger.info("[tlscontact] Found {} slot(s)", len(all_slots))
        return all_slots


def _parse_tls_calendar(body: Any, target: TargetConfig) -> list[SlotResult]:
    slots = []
    if isinstance(body, list):
        items = body
    elif isinstance(body, dict):
        items = body.get("dates", body.get("slots", []))
    else:
        return []

    for item in items:
        date_str = item.get("date", "") if isinstance(item, dict) else str(item)
        parsed = _parse_date(date_str)
        if parsed:
            slots.append(
                SlotResult(
                    provider="tlscontact",
                    country=target.country,
                    centre=target.centre,
                    visa_type=target.visa_type,
                    date=parsed,
                    booking_url=f"https://{_COUNTRY_SUBDOMAINS.get(target.country.lower(), 'fr')}.tlscontact.com/gb/lon/appointment",
                )
            )
    return slots


async def _parse_calendar_dom(page: Any, target: TargetConfig, base_url: str) -> list[SlotResult]:
    slots = []
    elements = await page.query_selector_all(
        ".available, [class*='available-day'], [data-date]:not([class*='disabled']):not([class*='past'])"
    )
    for el in elements:
        try:
            date_str = await el.get_attribute("data-date") or await el.inner_text()
            parsed = _parse_date(date_str.strip())
            if parsed:
                slots.append(
                    SlotResult(
                        provider="tlscontact",
                        country=target.country,
                        centre=target.centre,
                        visa_type=target.visa_type,
                        date=parsed,
                        booking_url=base_url + "/appointment",
                    )
                )
        except Exception:
            pass
    return slots
