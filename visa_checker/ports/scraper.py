"""Port: scraper interface."""
from __future__ import annotations

from abc import ABC, abstractmethod

from visa_checker.domain.models import SlotResult


class IScraper(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @abstractmethod
    async def is_logged_in(self) -> bool: ...

    @abstractmethod
    async def login(self) -> None: ...

    @abstractmethod
    async def check_slots(self) -> list[SlotResult]: ...

    async def run_once(self) -> list[SlotResult]:
        """Login if needed, then check slots. Raises ScraperError on failure."""
        if not await self.is_logged_in():
            await self.login()
        return await self.check_slots()
