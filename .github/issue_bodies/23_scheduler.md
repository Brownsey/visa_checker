## Summary
Build the main polling orchestrator that runs each scraper on a configurable interval with jitter, coordinates concurrent provider checks, and feeds results to the alert dispatcher.

## Design

```
APScheduler
    |
    +-- Job: poll_vfs_global()    every 90s ± 20%
    +-- Job: poll_tls_contact()   every 90s ± 20%
    +-- Job: poll_bls()           every 90s ± 20%
    |
    v
For each job:
  1. scraper.run_once() -> list[SlotResult]
  2. Filter: slot.is_within_range(config.earliest, config.latest)
  3. Filter: state.is_new(slot)
  4. dispatcher.dispatch(slot) for each new slot
  5. state.mark_seen(slot)
  6. state.log_poll(...)
```

## Tasks
- [ ] Create `Orchestrator` in `visa_checker/scheduler/orchestrator.py`
- [ ] Use `APScheduler` with `AsyncIOScheduler`
- [ ] Per-provider job with interval = `config.polling.interval_seconds * random.uniform(0.8, 1.2)`
- [ ] Stagger job start times on launch (spread initial polls by 10–30s) to avoid hammering all providers simultaneously
- [ ] Handle `ScraperError`: log + skip this poll cycle, do not crash the scheduler
- [ ] Hourly heartbeat log entry: "Still running. Polls: N, Slots found today: N"
- [ ] Graceful shutdown on SIGINT/SIGTERM: finish in-progress polls, then exit

## Acceptance Criteria
- All configured targets are polled independently
- A crash in one provider's scraper does not stop other providers from polling
- Jitter is applied so requests are not sent at exactly the same second each cycle
- Graceful shutdown completes without orphaned browser processes
