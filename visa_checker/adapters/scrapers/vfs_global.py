"""VFS Global scraper — covers Germany, Italy, Netherlands, Belgium, Denmark, Czech Republic, Ireland."""
from __future__ import annotations

import re
from datetime import date
from typing import Any

from loguru import logger

from visa_checker.adapters.browser.human import BehaviourConfig, human_click, human_type, random_mouse_movement
from visa_checker.adapters.scrapers.base import BaseScraper, register_scraper
from visa_checker.config.settings import TargetConfig
from visa_checker.domain.errors import AuthError, BlockedError, ScraperError
from visa_checker.domain.models import SlotResult
from visa_checker.ports.browser import IBrowserEngine
from visa_checker.ports.captcha import ICaptchaSolver

_COUNTRY_SLUGS: dict[str, str] = {
    "germany": "deu",
    "italy": "ita",
    "netherlands": "nld",
    "belgium": "bel",
    "denmark": "dnk",
    "czech republic": "cze",
    "ireland": "irl",
    "hungary": "hun",
    "latvia": "lva",
    "austria": "aut",
    "finland": "fin",
    "sweden": "swe",
    "norway": "nor",
    "poland": "pol",
    "spain": "esp",
}

_BASE_URL = "https://visa.vfsglobal.com/gbr/en"


@register_scraper("vfs_global")
class VFSGlobalScraper(BaseScraper):
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
        return "vfs_global"

    def _login_url(self) -> str:
        slug = _COUNTRY_SLUGS.get(self._target.country.lower(), self._target.country.lower())
        return f"{_BASE_URL}/{slug}/login"

    def _booking_url(self) -> str:
        slug = _COUNTRY_SLUGS.get(self._target.country.lower(), self._target.country.lower())
        return f"{_BASE_URL}/{slug}/book-an-appointment"

    async def _get_page(self) -> Any:
        if self._page is None or self._page.is_closed():
            self._page = await self._browser.new_page()
        return self._page

    async def is_logged_in(self) -> bool:
        try:
            page = await self._get_page()
            slug = _COUNTRY_SLUGS.get(self._target.country.lower(), self._target.country.lower())
            await page.goto(f"{_BASE_URL}/{slug}/dashboard", wait_until="domcontentloaded", timeout=15000)
            return "login" not in page.url
        except Exception:
            return False

    async def login(self) -> None:
        page = await self._get_page()
        await random_mouse_movement(page, cfg=self._behaviour)

        logger.info("[vfs_global] Navigating to login: {}", self._login_url())
        await page.goto(self._login_url(), wait_until="networkidle", timeout=30000)

        if "cloudflare" in (await page.content()).lower():
            raise BlockedError("VFS Global is behind Cloudflare — IP may be blocked")

        await human_type(page, "input[type=email]", self._email, cfg=self._behaviour)
        await human_type(page, "input[type=password]", self._password, cfg=self._behaviour)

        # Solve CAPTCHA unconditionally — solver returns "" if none is present
        if self._captcha_solver:
            await self._captcha_solver.solve(page)

        await human_click(page, "button[type=submit]", cfg=self._behaviour)
        await page.wait_for_load_state("networkidle", timeout=20000)

        if "login" in page.url or "invalid" in (await page.content()).lower():
            raise AuthError("VFS Global login failed — check credentials")

        logger.info("[vfs_global] Login successful")

    async def check_slots(self) -> list[SlotResult]:
        page = await self._get_page()
        logger.info("[vfs_global] Checking slots at {}", self._booking_url())

        await page.goto(self._booking_url(), wait_until="networkidle", timeout=30000)

        content = await page.content()

        if "no appointment" in content.lower() or "fully booked" in content.lower():
            logger.debug("[vfs_global] No slots available message detected")
            return []

        if "cloudflare" in content.lower():
            raise BlockedError("VFS Global blocked the request")

        slots: list[SlotResult] = []

        # Extract available dates from calendar/date-picker elements
        date_elements = await page.query_selector_all(
            ".available-date, [class*='available'], [data-date]:not([class*='disabled'])"
        )

        for el in date_elements:
            try:
                date_str = await el.get_attribute("data-date") or await el.inner_text()
                date_str = date_str.strip()
                parsed = _parse_date(date_str)
                if parsed is None:
                    continue
                slots.append(
                    SlotResult(
                        provider="vfs_global",
                        country=self._target.country,
                        centre=self._target.centre,
                        visa_type=self._target.visa_type,
                        date=parsed,
                        booking_url=self._booking_url(),
                    )
                )
            except Exception as exc:
                logger.debug("[vfs_global] Could not parse date element: {}", exc)

        logger.info("[vfs_global] Found {} slot(s)", len(slots))
        return slots


def _parse_date(raw: str) -> date | None:
    """Try multiple date formats."""
    import re as _re
    from datetime import datetime

    raw = raw.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d %B %Y", "%B %d, %Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue

    # Try ISO-like
    m = _re.search(r"(\d{4}-\d{2}-\d{2})", raw)
    if m:
        try:
            return date.fromisoformat(m.group(1))
        except ValueError:
            pass
    return None
