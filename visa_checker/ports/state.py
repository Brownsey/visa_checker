"""Port: state repository interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from visa_checker.domain.models import SlotResult


class IStateRepository(ABC):
    @abstractmethod
    async def initialise(self) -> None:
        """Create schema if not present. Must be called before other methods."""

    @abstractmethod
    async def is_new(self, slot: SlotResult) -> bool:
        """Return True if this slot_id has not been seen before."""

    @abstractmethod
    async def mark_seen(self, slot: SlotResult) -> None:
        """Upsert the slot into persistent storage."""

    @abstractmethod
    async def mark_alerted(self, slot_id: str) -> None:
        """Record that an alert was successfully dispatched for this slot."""

    @abstractmethod
    async def log_poll(
        self,
        provider: str,
        centre: str,
        checked_at: datetime,
        slots_found: int,
        duration_ms: int,
        error: str | None = None,
    ) -> None:
        """Append a poll log entry."""

    @abstractmethod
    async def get_history(self, days: int = 7) -> list[SlotResult]:
        """Return slots seen in the last N days."""
