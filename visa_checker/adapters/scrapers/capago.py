"""Capago scraper — Finland and Iceland Schengen visas from UK."""
from __future__ import annotations

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

_BASE_URL = "https://www.capago.eu"


@register_scraper("capago")
class CapagoScraper(BaseScraper):
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

    @property
    def provider_name(self) -> str:
        return "capago"

    async def _get_page(self) -> Any:
        if self._page is None or self._page.is_closed():
            self._page = await self._browser.new_page()
        return self._page

    async def is_logged_in(self) -> bool:
        try:
            page = await self._get_page()
            await page.goto(_BASE_URL + "/account", wait_until="domcontentloaded", timeout=15000)
            return "login" not in page.url
        except Exception:
            return False

    async def login(self) -> None:
        page = await self._get_page()
        await random_mouse_movement(page, cfg=self._behaviour)
        logger.info("[capago] Navigating to login")
        await page.goto(_BASE_URL + "/login", wait_until="networkidle", timeout=30000)

        if "cloudflare" in (await page.content()).lower():
            raise BlockedError("Capago blocked the request")

        await human_type(page, "input[type=email], input[name=email]", self._email, cfg=self._behaviour)
        await human_type(page, "input[type=password]", self._password, cfg=self._behaviour)

        has_captcha = await page.query_selector("[data-sitekey]")
        if has_captcha and self._captcha_solver:
            await self._captcha_solver.solve(page)

        await human_click(page, "button[type=submit]", cfg=self._behaviour)
        await page.wait_for_load_state("networkidle", timeout=20000)

        if "login" in page.url:
            raise AuthError("Capago login failed — check credentials")
        logger.info("[capago] Login successful")

    async def check_slots(self) -> list[SlotResult]:
        page = await self._get_page()
        country_slug = self._target.country.lower().replace(" ", "-")
        appointment_url = f"{_BASE_URL}/appointment/{country_slug}"
        logger.info("[capago] Checking slots at {}", appointment_url)
        await page.goto(appointment_url, wait_until="networkidle", timeout=30000)

        content = await page.content()
        if "no appointment" in content.lower() or "fully booked" in content.lower():
            return []

        slots: list[SlotResult] = []
        date_elements = await page.query_selector_all(
            "[data-date]:not(.disabled), .available-date, .slot-open"
        )
        for el in date_elements:
            try:
                date_str = await el.get_attribute("data-date") or await el.inner_text()
                parsed = _parse_date(date_str.strip())
                if parsed:
                    slots.append(
                        SlotResult(
                            provider="capago",
                            country=self._target.country,
                            centre=self._target.centre,
                            visa_type=self._target.visa_type,
                            date=parsed,
                            booking_url=appointment_url,
                        )
                    )
            except Exception:
                pass

        logger.info("[capago] Found {} slot(s)", len(slots))
        return slots
