"""Port: CAPTCHA solver interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ICaptchaSolver(ABC):
    @abstractmethod
    async def solve(self, page: Any) -> str:
        """Detect, solve, and inject a CAPTCHA on the given page. Returns the token."""
