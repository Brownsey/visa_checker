"""BLS International scraper — Spain visa appointments from UK centres."""
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

_BASE_URL = "https://uk.blsspainvisa.com"

_CENTRE_IDS: dict[str, str] = {
    "london": "1",
    "edinburgh": "2",
    "manchester": "3",
}


@register_scraper("bls")
class BLSInternationalScraper(BaseScraper):
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
        return "bls"

    async def _get_page(self) -> Any:
        if self._page is None or self._page.is_closed():
            self._page = await self._browser.new_page()
        return self._page

    async def is_logged_in(self) -> bool:
        try:
            page = await self._get_page()
            await page.goto(_BASE_URL + "/london/index.php/account", wait_until="domcontentloaded", timeout=15000)
            return "login" not in page.url
        except Exception:
            return False

    async def login(self) -> None:
        page = await self._get_page()
        await random_mouse_movement(page, cfg=self._behaviour)
        logger.info("[bls] Navigating to BLS login")
        await page.goto(_BASE_URL + "/london/index.php/account/login", wait_until="networkidle", timeout=30000)

        content = await page.content()
        if "cloudflare" in content.lower():
            raise BlockedError("BLS blocked the request")

        await human_type(page, "input[name=email], input[type=email]", self._email, cfg=self._behaviour)
        await human_type(page, "input[name=password], input[type=password]", self._password, cfg=self._behaviour)
        await human_click(page, "button[type=submit], input[type=submit]", cfg=self._behaviour)
        await page.wait_for_load_state("networkidle", timeout=20000)

        if "login" in page.url:
            raise AuthError("BLS login failed — check credentials")
        logger.info("[bls] Login successful")

    async def check_slots(self) -> list[SlotResult]:
        page = await self._get_page()
        centre_id = _CENTRE_IDS.get(self._target.centre.lower(), "1")
        appointment_url = f"{_BASE_URL}/london/index.php/appointment?centre={centre_id}"
        logger.info("[bls] Checking slots at {}", appointment_url)
        await page.goto(appointment_url, wait_until="networkidle", timeout=30000)

        content = await page.content()
        if "no appointment" in content.lower() or "not available" in content.lower():
            return []

        slots: list[SlotResult] = []
        date_elements = await page.query_selector_all(
            ".available-slot, [data-date]:not(.disabled), .slot-available"
        )
        for el in date_elements:
            try:
                date_str = await el.get_attribute("data-date") or await el.inner_text()
                parsed = _parse_date(date_str.strip())
                if parsed:
                    slots.append(
                        SlotResult(
                            provider="bls",
                            country=self._target.country,
                            centre=self._target.centre,
                            visa_type=self._target.visa_type,
                            date=parsed,
                            booking_url=appointment_url,
                        )
                    )
            except Exception:
                pass

        logger.info("[bls] Found {} slot(s)", len(slots))
        return slots
