"""Core domain models — pure Python, zero I/O dependencies."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timezone
from typing import Literal

ProviderName = Literal["vfs_global", "tlscontact", "bls", "capago"]


@dataclass(frozen=True)
class SlotResult:
    """A single available appointment slot returned by a scraper.

    Immutable so it can be safely used as a dict key or stored in sets.
    """

    provider: ProviderName
    country: str
    centre: str
    visa_type: str
    date: date
    booking_url: str
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    time: time | None = None

    @property
    def slot_id(self) -> str:
        """Stable deduplication key — same slot on same day always matches."""
        return f"{self.provider}:{self.country.lower()}:{self.centre.lower()}:{self.date.isoformat()}"

    def is_within_range(self, earliest: date, latest: date) -> bool:
        """True if this slot's date falls within [earliest, latest] inclusive."""
        return earliest <= self.date <= latest

    def human_date(self) -> str:
        """e.g. 'Tuesday 15 July 2026'"""
        return self.date.strftime("%A %d %B %Y")

    def human_time(self) -> str:
        """e.g. '10:30 AM' or 'Any time'"""
        if self.time is None:
            return "Any time"
        return self.time.strftime("%I:%M %p").lstrip("0")


@dataclass(frozen=True)
class SlotTarget:
    """The user's desired appointment target — mirrors TargetConfig but is a domain object."""

    country: str
    provider: ProviderName
    centre: str
    visa_type: str
    earliest_date: date
    latest_date: date
