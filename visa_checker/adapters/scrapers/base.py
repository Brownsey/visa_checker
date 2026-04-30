"""Base scraper with shared login/slot-check orchestration and scraper registry."""
from __future__ import annotations

from typing import TYPE_CHECKING, Type

from loguru import logger

from visa_checker.domain.errors import ScraperError
from visa_checker.domain.models import SlotResult
from visa_checker.ports.scraper import IScraper

if TYPE_CHECKING:
    pass

_REGISTRY: dict[str, Type[IScraper]] = {}


def register_scraper(name: str):
    """Class decorator to register a scraper by provider name."""
    def decorator(cls: Type[IScraper]) -> Type[IScraper]:
        _REGISTRY[name] = cls
        return cls
    return decorator


def get_scraper_class(provider: str) -> Type[IScraper]:
    if provider not in _REGISTRY:
        raise KeyError(f"Unknown provider '{provider}'. Available: {list(_REGISTRY)}")
    return _REGISTRY[provider]


class BaseScraper(IScraper):
    """Concrete base with run_once error-handling and logging."""

    async def run_once(self) -> list[SlotResult]:
        provider = self.provider_name
        try:
            if not await self.is_logged_in():
                logger.info("[{}] Session not valid, logging in…", provider)
                await self.login()
            slots = await self.check_slots()
            logger.info("[{}] Check complete — {} slot(s) found", provider, len(slots))
            return slots
        except ScraperError:
            raise
        except Exception as exc:
            raise ScraperError(f"[{provider}] Unexpected error: {exc}") from exc
