"""Tests for AlertDispatcher."""
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from visa_checker.application.alert_dispatcher import AlertDispatcher
from visa_checker.domain.errors import AlertError
from visa_checker.domain.models import SlotResult


def _slot() -> SlotResult:
    return SlotResult(
        provider="vfs_global",
        country="Germany",
        centre="London",
        visa_type="short_stay",
        date=date(2026, 7, 15),
        booking_url="https://example.com",
        checked_at=datetime(2026, 4, 29, 12, 0, tzinfo=timezone.utc),
    )


async def test_dispatch_calls_all_channels(state, mock_alert_channel):
    ch2 = MagicMock()
    ch2.channel_name = "ch2"
    ch2.send = AsyncMock()
    dispatcher = AlertDispatcher([mock_alert_channel, ch2], state)
    slot = _slot()
    await state.mark_seen(slot)
    await dispatcher.dispatch(slot)
    mock_alert_channel.send.assert_awaited_once_with(slot)
    ch2.send.assert_awaited_once_with(slot)


async def test_dispatch_marks_alerted_on_success(state, mock_alert_channel):
    dispatcher = AlertDispatcher([mock_alert_channel], state)
    slot = _slot()
    await state.mark_seen(slot)
    await dispatcher.dispatch(slot)
    # After dispatch, slot should be marked alerted in DB
    # Verify by checking the state directly
    async with state._db.execute(
        "SELECT alerted FROM slots WHERE slot_id = ?", (slot.slot_id,)
    ) as cur:
        row = await cur.fetchone()
    assert row is not None
    assert row["alerted"] == 1


async def test_dispatch_one_channel_fails_others_still_fire(state):
    bad = MagicMock()
    bad.channel_name = "bad"
    bad.send = AsyncMock(side_effect=AlertError("network error"))

    good = MagicMock()
    good.channel_name = "good"
    good.send = AsyncMock()

    dispatcher = AlertDispatcher([bad, good], state)
    slot = _slot()
    await state.mark_seen(slot)
    await dispatcher.dispatch(slot)
    good.send.assert_awaited_once_with(slot)


async def test_test_all_returns_results(state, mock_alert_channel):
    dispatcher = AlertDispatcher([mock_alert_channel], state)
    results = await dispatcher.test_all()
    assert results == {"mock": True}
    mock_alert_channel.send_test.assert_awaited_once()
