"""Port: browser engine interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class IBrowserEngine(ABC):
    @abstractmethod
    async def start(self) -> None: ...

    @abstractmethod
    async def stop(self) -> None: ...

    @abstractmethod
    async def new_page(self, proxy: dict[str, str] | None = None) -> Any:
        """Return a new browser page (Playwright Page or equivalent)."""

    async def __aenter__(self) -> "IBrowserEngine":
        await self.start()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.stop()
