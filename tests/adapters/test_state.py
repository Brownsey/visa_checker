"""Tests for SQLiteStateRepository."""
from datetime import date, datetime, timezone

import pytest

from visa_checker.adapters.state.sqlite_repository import SQLiteStateRepository
from visa_checker.domain.models import SlotResult


def _slot(slot_date=date(2026, 7, 15)) -> SlotResult:
    return SlotResult(
        provider="vfs_global",
        country="Germany",
        centre="London",
        visa_type="short_stay",
        date=slot_date,
        booking_url="https://example.com",
        checked_at=datetime(2026, 4, 29, 12, 0, tzinfo=timezone.utc),
    )


async def test_is_new_initially_true(state):
    slot = _slot()
    assert await state.is_new(slot) is True


async def test_is_new_after_mark_seen_false(state):
    slot = _slot()
    await state.mark_seen(slot)
    assert await state.is_new(slot) is False


async def test_mark_seen_idempotent(state):
    slot = _slot()
    await state.mark_seen(slot)
    await state.mark_seen(slot)  # should not raise
    assert await state.is_new(slot) is False


async def test_different_slots_independent(state):
    s1 = _slot(date(2026, 7, 15))
    s2 = _slot(date(2026, 7, 16))
    await state.mark_seen(s1)
    assert await state.is_new(s2) is True


async def test_mark_alerted(state):
    slot = _slot()
    await state.mark_seen(slot)
    await state.mark_alerted(slot.slot_id)  # should not raise


async def test_log_poll(state):
    await state.log_poll(
        provider="vfs_global",
        centre="London",
        checked_at=datetime.now(timezone.utc),
        slots_found=3,
        duration_ms=450,
    )


async def test_get_history_empty(state):
    result = await state.get_history(days=7)
    assert result == []


async def test_get_history_returns_seen_slots(state):
    slot = _slot()
    await state.mark_seen(slot)
    result = await state.get_history(days=7)
    assert len(result) == 1
    assert result[0].slot_id == slot.slot_id
