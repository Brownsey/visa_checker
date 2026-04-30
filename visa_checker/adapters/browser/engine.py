"""Playwright browser engine with stealth patches applied (IBrowserEngine adapter)."""
from __future__ import annotations

import asyncio
import random
from typing import Any

from loguru import logger
from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright

from visa_checker.adapters.anti_detection.fingerprint import FingerprintProfile, FingerprintRotator
from visa_checker.ports.browser import IBrowserEngine
from visa_checker.ports.proxy import IProxyProvider, ProxyConfig

_STEALTH_SCRIPT = """
() => {
    // Hide webdriver flag
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

    // Populate plugins
    Object.defineProperty(navigator, 'plugins', {
        get: () => [1, 2, 3, 4, 5],
    });

    // Populate languages
    Object.defineProperty(navigator, 'languages', {
        get: () => ['en-GB', 'en'],
    });

    // Add chrome object
    window.chrome = { runtime: {} };

    // Remove headless traces
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications'
            ? Promise.resolve({ state: Notification.permission })
            : originalQuery(parameters)
    );
}
"""


class PlaywrightBrowserEngine(IBrowserEngine):
    def __init__(
        self,
        headless: bool = True,
        proxy_provider: IProxyProvider | None = None,
        fingerprint_rotator: FingerprintRotator | None = None,
    ) -> None:
        self._headless = headless
        self._proxy_provider = proxy_provider
        self._fingerprint_rotator = fingerprint_rotator or FingerprintRotator()
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None

    async def start(self) -> None:
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self._headless,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
            ],
        )
        logger.info("Browser started (headless={})", self._headless)

    async def stop(self) -> None:
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("Browser stopped")

    async def new_page(self, proxy: dict[str, str] | None = None) -> Page:
        assert self._browser is not None, "Call start() first"

        profile = self._fingerprint_rotator.next()

        # Resolve proxy — try up to all available proxies on connection failure
        playwright_proxy = None
        _active_proxy_config: ProxyConfig | None = None

        if proxy:
            playwright_proxy = proxy
        elif self._proxy_provider:
            _active_proxy_config = self._proxy_provider.next()
            if _active_proxy_config:
                playwright_proxy = {
                    "server": _active_proxy_config.server,
                    **(
                        {"username": _active_proxy_config.username, "password": _active_proxy_config.password}
                        if _active_proxy_config.username
                        else {}
                    ),
                }

        for _attempt in range(10):  # retry with different proxies on connection failure
            try:
                context: BrowserContext = await self._browser.new_context(
                    user_agent=profile.user_agent,
                    viewport={"width": profile.viewport[0], "height": profile.viewport[1]},
                    locale=profile.locale,
                    timezone_id=profile.timezone,
                    proxy=playwright_proxy,
                    extra_http_headers={"Accept-Language": f"{profile.locale},en;q=0.9"},
                )
                break
            except Exception as exc:
                if _active_proxy_config and hasattr(self._proxy_provider, "mark_failed"):
                    logger.warning(
                        "Proxy {} failed ({}), trying next proxy",
                        _active_proxy_config.server, exc,
                    )
                    self._proxy_provider.mark_failed(_active_proxy_config.server)  # type: ignore[union-attr]
                    _active_proxy_config = self._proxy_provider.next()
                    if _active_proxy_config:
                        playwright_proxy = {
                            "server": _active_proxy_config.server,
                            **(
                                {"username": _active_proxy_config.username, "password": _active_proxy_config.password}
                                if _active_proxy_config.username
                                else {}
                            ),
                        }
                    else:
                        playwright_proxy = None
                else:
                    raise
        else:
            raise RuntimeError("Could not open browser context after trying all proxies")

        page: Page = await context.new_page()

        # Apply stealth patches on every navigation
        await page.add_init_script(_STEALTH_SCRIPT)

        # Small startup jitter
        await asyncio.sleep(random.uniform(1.0, 3.0))

        return page
