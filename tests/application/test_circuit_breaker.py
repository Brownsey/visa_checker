"""Tests for CircuitBreaker."""
import pytest

from visa_checker.application.circuit_breaker import CircuitBreaker, CircuitState, _FAILURE_THRESHOLD
from visa_checker.domain.errors import CircuitOpenError, ScraperError


async def test_circuit_starts_closed():
    cb = CircuitBreaker("test")
    assert cb.state == CircuitState.CLOSED


async def test_successful_call_stays_closed():
    cb = CircuitBreaker("test")

    async def ok():
        return 42

    result = await cb.call(ok())
    assert result == 42
    assert cb.state == CircuitState.CLOSED


async def test_circuit_opens_after_threshold():
    cb = CircuitBreaker("test")

    async def fail():
        raise ScraperError("boom")

    for _ in range(_FAILURE_THRESHOLD):
        with pytest.raises(ScraperError):
            await cb.call(fail())

    assert cb.state == CircuitState.OPEN


async def test_open_circuit_raises_circuit_open_error():
    cb = CircuitBreaker("test")

    async def fail():
        raise ScraperError("boom")

    for _ in range(_FAILURE_THRESHOLD):
        with pytest.raises(ScraperError):
            await cb.call(fail())

    async def ok():
        return 1

    with pytest.raises(CircuitOpenError):
        await cb.call(ok())


async def test_success_resets_failure_count():
    cb = CircuitBreaker("test")

    async def fail():
        raise ScraperError("boom")

    async def ok():
        return True

    # Accumulate some failures but not enough to open
    for _ in range(_FAILURE_THRESHOLD - 1):
        with pytest.raises(ScraperError):
            await cb.call(fail())

    await cb.call(ok())
    assert cb._failures == 0
    assert cb.state == CircuitState.CLOSED
