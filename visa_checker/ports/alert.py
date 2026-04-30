"""Port: alert channel interface."""
from __future__ import annotations

from abc import ABC, abstractmethod

from visa_checker.domain.models import SlotResult


class IAlertChannel(ABC):
    @property
    @abstractmethod
    def channel_name(self) -> str: ...

    @abstractmethod
    async def send(self, slot: SlotResult) -> None:
        """Send a slot-available notification. Raises AlertError on failure."""

    @abstractmethod
    async def send_test(self) -> None:
        """Send a test message to verify the channel is configured correctly."""
