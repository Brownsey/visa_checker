"""Tests for SlotResult domain model."""
from datetime import date, datetime, timezone

import pytest

from visa_checker.domain.models import SlotResult


def make_slot(slot_date=date(2026, 7, 15), country="Germany", centre="London") -> SlotResult:
    return SlotResult(
        provider="vfs_global",
        country=country,
        centre=centre,
        visa_type="short_stay",
        date=slot_date,
        booking_url="https://example.com/book",
        checked_at=datetime(2026, 4, 29, 12, 0, tzinfo=timezone.utc),
    )


def test_slot_id_stable():
    s1 = make_slot()
    s2 = make_slot()
    assert s1.slot_id == s2.slot_id


def test_slot_id_differs_by_date():
    s1 = make_slot(slot_date=date(2026, 7, 15))
    s2 = make_slot(slot_date=date(2026, 7, 16))
    assert s1.slot_id != s2.slot_id


def test_slot_id_differs_by_country():
    s1 = make_slot(country="Germany")
    s2 = make_slot(country="France")
    assert s1.slot_id != s2.slot_id


def test_is_within_range_inclusive():
    slot = make_slot(slot_date=date(2026, 7, 15))
    assert slot.is_within_range(date(2026, 7, 15), date(2026, 7, 15))


def test_is_within_range_inside():
    slot = make_slot(slot_date=date(2026, 7, 15))
    assert slot.is_within_range(date(2026, 6, 1), date(2026, 9, 30))


def test_is_within_range_outside():
    slot = make_slot(slot_date=date(2026, 5, 1))
    assert not slot.is_within_range(date(2026, 6, 1), date(2026, 9, 30))


def test_is_within_range_lower_boundary():
    slot = make_slot(slot_date=date(2026, 5, 31))
    assert not slot.is_within_range(date(2026, 6, 1), date(2026, 9, 30))


def test_human_date_format():
    slot = make_slot(slot_date=date(2026, 7, 15))
    assert slot.human_date() == "Wednesday 15 July 2026"


def test_human_time_none():
    slot = make_slot()
    assert slot.human_time() == "Any time"


def test_slot_is_frozen():
    slot = make_slot()
    with pytest.raises((AttributeError, TypeError)):
        slot.country = "France"  # type: ignore[misc]
