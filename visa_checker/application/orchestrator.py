"""APScheduler-based polling orchestrator with per-provider jitter and circuit breaking."""
from __future__ import annotations

import asyncio
import random
import time
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger

from visa_checker.application.alert_dispatcher import AlertDispatcher
from visa_checker.application.circuit_breaker import CircuitBreaker
from visa_checker.config.settings import Settings
from visa_checker.domain.errors import CircuitOpenError, ScraperError
from visa_checker.ports.scraper import IScraper
from visa_checker.ports.state import IStateRepository


class Orchestrator:
    def __init__(
        self,
        scrapers: list[IScraper],
        dispatcher: AlertDispatcher,
        state: IStateRepository,
        settings: Settings,
    ) -> None:
        self._scrapers = scrapers
        self._dispatcher = dispatcher
        self._state = state
        self._settings = settings
        self._scheduler = AsyncIOScheduler()
        self._breakers: dict[str, CircuitBreaker] = {
            s.provider_name: CircuitBreaker(s.provider_name) for s in scrapers
        }
        self._poll_count = 0
        self._slots_today = 0

    def _interval_with_jitter(self) -> float:
        base = self._settings.polling.interval_seconds
        jitter = self._settings.polling.jitter_pct
        return base * random.uniform(1 - jitter, 1 + jitter)

    async def _poll_scraper(self, scraper: IScraper, target_index: int) -> None:
        breaker = self._breakers[scraper.provider_name]
        start = time.monotonic()
        error_msg: str | None = None

        try:
            slots = await breaker.call(scraper.run_once())
        except CircuitOpenError as exc:
            logger.warning(str(exc))
            return
        except ScraperError as exc:
            error_msg = str(exc)
            logger.error("[{}] Poll failed: {}", scraper.provider_name, exc)
            slots = []
        except Exception as exc:
            error_msg = str(exc)
            logger.exception("[{}] Unexpected poll error", scraper.provider_name)
            slots = []

        duration_ms = int((time.monotonic() - start) * 1000)
        target = self._settings.targets[target_index]

        # Filter to date range and new slots
        in_range = [s for s in slots if s.is_within_range(target.earliest_date, target.latest_date)]
        new_slots = []
        for slot in in_range:
            if await self._state.is_new(slot):
                new_slots.append(slot)
                await self._state.mark_seen(slot)

        self._poll_count += 1
        self._slots_today += len(new_slots)

        await self._state.log_poll(
            provider=scraper.provider_name,
            centre=target.centre,
            checked_at=datetime.now(timezone.utc),
            slots_found=len(slots),
            duration_ms=duration_ms,
            error=error_msg,
        )

        for slot in new_slots:
            logger.info("New slot found: {} — dispatching alert", slot.slot_id)
            await self._dispatcher.dispatch(slot)

    def _schedule_scraper(self, scraper: IScraper, target_index: int, start_delay: float) -> None:
        interval = self._interval_with_jitter()

        async def job() -> None:
            await self._poll_scraper(scraper, target_index)
            # Reschedule with fresh jitter each time
            self._scheduler.add_job(
                job,
                "date",
                run_date=None,
                misfire_grace_time=30,
            )

        # Use interval trigger; stagger initial fire by start_delay
        self._scheduler.add_job(
            self._poll_scraper,
            "interval",
            seconds=self._settings.polling.interval_seconds,
            jitter=int(self._settings.polling.interval_seconds * self._settings.polling.jitter_pct),
            args=[scraper, target_index],
            next_run_time=datetime.now(timezone.utc).__class__.now(timezone.utc).__class__.now(
                timezone.utc
            ),
            id=f"poll_{scraper.provider_name}_{target_index}",
        )

    def _heartbeat(self) -> None:
        logger.info(
            "Heartbeat — polls: {}, new slots today: {}, breaker states: {}",
            self._poll_count,
            self._slots_today,
            {p: b.state.value for p, b in self._breakers.items()},
        )

    async def start(self) -> None:
        logger.info("Orchestrator starting with {} scraper(s)", len(self._scrapers))
        for i, scraper in enumerate(self._scrapers):
            # Stagger initial polls by 10–30s each
            delay = i * random.uniform(10, 30)
            self._scheduler.add_job(
                self._poll_scraper,
                "interval",
                seconds=self._settings.polling.interval_seconds,
                jitter=int(self._settings.polling.interval_seconds * self._settings.polling.jitter_pct),
                args=[scraper, i],
                id=f"poll_{scraper.provider_name}_{i}",
            )
        self._scheduler.add_job(self._heartbeat, "interval", hours=1)
        self._scheduler.start()
        logger.info("Scheduler started")

    async def stop(self) -> None:
        self._scheduler.shutdown(wait=False)
        logger.info("Orchestrator stopped")

    def circuit_statuses(self) -> list[dict]:
        return [b.status() for b in self._breakers.values()]
