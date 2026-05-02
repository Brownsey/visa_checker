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

    async def _dismiss_cookies(self, page: Any) -> None:
        """Dismiss GDPR cookie banner if present — must run before any form interaction."""
        try:
            btn = await page.query_selector(
                "button:has-text('Reject All'), button:has-text('Reject all'), "
                "button:has-text('Decline'), button:has-text('Accept All'), "
                "button[id*='cookie'], button[class*='cookie-reject']"
            )
            if btn:
                await btn.click()
                await page.wait_for_load_state("domcontentloaded", timeout=5000)
                logger.debug("[vfs_global] Cookie banner dismissed")
        except Exception:
            pass

    async def login(self) -> None:
        page = await self._get_page()
        await random_mouse_movement(page, cfg=self._behaviour)

        logger.info("[vfs_global] Navigating to login: {}", self._login_url())
        await page.goto(self._login_url(), wait_until="networkidle", timeout=30000)

        if "cloudflare" in (await page.content()).lower():
            raise BlockedError("VFS Global is behind Cloudflare — IP may be blocked")

        await self._dismiss_cookies(page)

        # VFS Global uses Angular Material — prefer mat-input IDs; fall back to generic
        email_sel = "#mat-input-0, input[type=email]"
        pass_sel = "#mat-input-1, input[type=password]"
        await human_type(page, email_sel, self._email, cfg=self._behaviour)
        await human_type(page, pass_sel, self._password, cfg=self._behaviour)

        # Solve CAPTCHA unconditionally — solver returns "" if none is present
        if self._captcha_solver:
            await self._captcha_solver.solve(page)

        await human_click(page, "button[type=submit], button:has-text('Sign In')", cfg=self._behaviour)

        # Wait for dashboard indicator rather than just URL check
        try:
            await page.wait_for_selector(
                "button:has-text('Start New Booking'), [class*='dashboard']",
                timeout=20000,
            )
        except Exception:
            if "login" in page.url or "invalid" in (await page.content()).lower():
                raise AuthError("VFS Global login failed — check credentials")

        logger.info("[vfs_global] Login successful")

    async def _select_dropdown(self, page: Any, nth: int, value: str) -> None:
        """Select an option from the nth mat-form-field dropdown by visible text."""
        fields = await page.query_selector_all("mat-form-field")
        if nth >= len(fields):
            raise ScraperError(f"[vfs_global] Expected dropdown #{nth} but only {len(fields)} found")
        await fields[nth].click()
        await page.wait_for_selector("mat-option", timeout=10000)
        option = await page.query_selector(f"mat-option:has-text('{value}')")
        if option is None:
            raise ScraperError(f"[vfs_global] Option '{value}' not found in dropdown #{nth}")
        await option.click()
        await page.wait_for_load_state("domcontentloaded", timeout=10000)

    async def check_slots(self) -> list[SlotResult]:
        page = await self._get_page()
        booking_url = self._booking_url()
        logger.info("[vfs_global] Navigating to booking page: {}", booking_url)

        await page.goto(booking_url, wait_until="networkidle", timeout=30000)

        content = await page.content()
        if "cloudflare" in content.lower():
            raise BlockedError("VFS Global blocked the request")

        # Step 1 — click "Start New Booking" to enter the wizard
        try:
            await human_click(page, "button:has-text('Start New Booking')", cfg=self._behaviour)
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception as exc:
            raise ScraperError(f"[vfs_global] Could not start booking wizard: {exc}") from exc

        # Step 2 — select visa centre (1st dropdown)
        await self._select_dropdown(page, 0, self._target.centre)

        # Step 3 — select visa category (2nd dropdown, mapped from visa_type)
        await self._select_dropdown(page, 1, self._target.visa_type)

        # Step 4 — select visa subcategory (3rd dropdown) if configured
        if self._target.visa_sub_category:
            await self._select_dropdown(page, 2, self._target.visa_sub_category)

        # Step 5 — wait for availability alert and extract dates from div.alert text
        slots: list[SlotResult] = []
        try:
            await page.wait_for_selector("div.alert", timeout=15000)
        except Exception:
            logger.debug("[vfs_global] No div.alert appeared — assuming no slots")
            return slots

        alert_elements = await page.query_selector_all("div.alert")
        for el in alert_elements:
            try:
                text = await el.inner_text()
                text = text.strip()
                if "no appointment" in text.lower() or "fully booked" in text.lower():
                    continue
                parsed = _parse_date(text)
                if parsed is None:
                    continue
                slots.append(
                    SlotResult(
                        provider="vfs_global",
                        country=self._target.country,
                        centre=self._target.centre,
                        visa_type=self._target.visa_type,
                        date=parsed,
                        booking_url=booking_url,
                    )
                )
            except Exception as exc:
                logger.debug("[vfs_global] Could not parse alert element: {}", exc)

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
