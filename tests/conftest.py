"""Shared pytest fixtures.

All fixtures that involve network I/O (browser, httpx) are wired through
the FileProxyProvider so that test traffic routes via proxies.txt when
proxies are available. Unit tests that mock network calls are unaffected.
"""
from __future__ import annotations

import os
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from visa_checker.adapters.anti_detection.proxy import FileProxyProvider, NullProxyProvider
from visa_checker.adapters.state.sqlite_repository import SQLiteStateRepository
from visa_checker.domain.models import SlotResult
from visa_checker.ports.proxy import IProxyProvider


# ---------------------------------------------------------------------------
# Proxy fixture — loaded once per session; all network fixtures use it
# ---------------------------------------------------------------------------

_PROXIES_FILE = str(Path(__file__).parent.parent / "proxies.txt")


@pytest.fixture(scope="session")
def proxy_provider() -> IProxyProvider:
    """Load FileProxyProvider from proxies.txt (project root).

    Falls back to NullProxyProvider if the file is absent so that tests
    can still run in CI without a proxies.txt.
    """
    if Path(_PROXIES_FILE).exists():
        provider = FileProxyProvider(_PROXIES_FILE)
        if provider._active:
            return provider
    return NullProxyProvider()


@pytest.fixture(scope="session", autouse=True)
def set_proxy_env(proxy_provider: IProxyProvider) -> None:
    """Set HTTPS_PROXY / HTTP_PROXY env vars for the test session.

    This ensures that any httpx.AsyncClient or requests calls made during
    tests (e.g. alert channels, CAPTCHA solver) automatically route through
    the proxy without requiring explicit proxy arguments.
    """
    proxy = proxy_provider.next()
    if proxy is None:
        return

    proxy_url = proxy.server
    if proxy.username:
        # Embed credentials in the URL for libraries that read env vars
        from urllib.parse import urlparse
        parsed = urlparse(proxy.server)
        proxy_url = f"http://{proxy.username}:{proxy.password}@{parsed.hostname}:{parsed.port}"

    os.environ.setdefault("HTTP_PROXY", proxy_url)
    os.environ.setdefault("HTTPS_PROXY", proxy_url)


# ---------------------------------------------------------------------------
# Domain fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def slot_factory():
    """Factory for creating SlotResult instances with sane defaults."""
    def _make(
        provider="vfs_global",
        country="Germany",
        centre="London",
        visa_type="short_stay",
        slot_date=date(2026, 7, 15),
        booking_url="https://visa.vfsglobal.com/gbr/en/deu/book",
    ) -> SlotResult:
        return SlotResult(
            provider=provider,
            country=country,
            centre=centre,
            visa_type=visa_type,
            date=slot_date,
            booking_url=booking_url,
            checked_at=datetime(2026, 4, 29, 12, 0, 0, tzinfo=timezone.utc),
        )
    return _make


@pytest.fixture
async def state():
    """In-memory SQLite state repository."""
    repo = SQLiteStateRepository(":memory:")
    await repo.initialise()
    yield repo
    await repo.close()


@pytest.fixture
def mock_alert_channel():
    """Mock IAlertChannel."""
    channel = MagicMock()
    channel.channel_name = "mock"
    channel.send = AsyncMock()
    channel.send_test = AsyncMock()
    return channel
