## Summary
Implement per-provider exponential backoff and a circuit breaker so repeated scraper failures back off gracefully instead of hammering a blocked endpoint.

## Behaviour

| Consecutive failures | Next retry delay |
|---|---|
| 1 | 2 min |
| 2 | 4 min |
| 3 | 8 min |
| 4 | 16 min |
| 5+ | 30 min (cap) |

After 5 consecutive failures, the circuit opens and the provider is paused for 30 minutes, then retried once. On success, the circuit resets.

## Tasks
- [ ] Create `CircuitBreaker` in `visa_checker/scheduler/circuit_breaker.py`
- [ ] States: CLOSED (normal), OPEN (paused), HALF_OPEN (testing recovery)
- [ ] `CircuitBreaker.call(coro)` — wraps a coroutine; raises `CircuitOpenError` when OPEN
- [ ] Each provider gets its own `CircuitBreaker` instance
- [ ] State (failure count, next retry time) persisted to the `state.db` so it survives restarts
- [ ] Send an alert notification when a circuit opens: "WARNING: VFS Global scraper is paused after 5 consecutive failures. Will retry at 15:30 UTC."
- [ ] Send an alert notification when a circuit recovers

## Acceptance Criteria
- After 5 simulated consecutive `ScraperError` raises, the circuit opens
- Circuit opens within the correct delay window after opening
- Recovery notification is sent when the scraper succeeds after circuit was open
