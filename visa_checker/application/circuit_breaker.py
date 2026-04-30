"""Per-provider circuit breaker with exponential backoff."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Awaitable, Callable, TypeVar

from loguru import logger

from visa_checker.domain.errors import CircuitOpenError

T = TypeVar("T")

_BACKOFF_TABLE = [2, 4, 8, 16, 30]  # minutes per consecutive failure
_FAILURE_THRESHOLD = 5


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Wraps a coroutine and opens after FAILURE_THRESHOLD consecutive failures."""

    def __init__(self, provider: str) -> None:
        self._provider = provider
        self._failures = 0
        self._state = CircuitState.CLOSED
        self._retry_at: datetime | None = None

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if self._retry_at and datetime.now(timezone.utc) >= self._retry_at:
                self._state = CircuitState.HALF_OPEN
                logger.info("[{}] Circuit half-open — testing recovery", self._provider)
        return self._state

    async def call(self, coro: Awaitable[T]) -> T:
        if self.state == CircuitState.OPEN:
            raise CircuitOpenError(
                f"[{self._provider}] Circuit is open until {self._retry_at}"
            )

        try:
            result = await coro
            self._on_success()
            return result
        except Exception as exc:
            self._on_failure()
            raise

    def _on_success(self) -> None:
        if self._state != CircuitState.CLOSED:
            logger.info("[{}] Circuit closed — provider recovered", self._provider)
        self._failures = 0
        self._state = CircuitState.CLOSED
        self._retry_at = None

    def _on_failure(self) -> None:
        self._failures += 1
        if self._failures >= _FAILURE_THRESHOLD:
            wait_minutes = _BACKOFF_TABLE[min(self._failures - _FAILURE_THRESHOLD, len(_BACKOFF_TABLE) - 1)]
            self._retry_at = datetime.now(timezone.utc) + timedelta(minutes=wait_minutes)
            self._state = CircuitState.OPEN
            logger.error(
                "[{}] Circuit OPENED after {} failures. Retry at {}",
                self._provider, self._failures, self._retry_at,
            )
        else:
            logger.warning(
                "[{}] Failure {}/{} before circuit opens",
                self._provider, self._failures, _FAILURE_THRESHOLD,
            )

    def status(self) -> dict[str, Any]:
        return {
            "provider": self._provider,
            "state": self.state.value,
            "consecutive_failures": self._failures,
            "retry_at": self._retry_at.isoformat() if self._retry_at else None,
        }
