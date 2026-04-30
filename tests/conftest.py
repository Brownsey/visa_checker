"""Shared pytest fixtures."""
from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from visa_checker.adapters.state.sqlite_repository import SQLiteStateRepository
from visa_checker.domain.models import SlotResult


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
