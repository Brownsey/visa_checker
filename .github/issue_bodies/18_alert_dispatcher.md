## Summary
Build the alert dispatcher that fans out new slot notifications to all configured channels, with retry logic and deduplication.

## Design

```
Scheduler finds new slot
        |
        v
AlertDispatcher.dispatch(slot)
        |
        +---> TelegramChannel.send(slot)
        |
        +---> EmailChannel.send(slot)
        |
        +---> NtfyChannel.send(slot)
        |
        +---> SMSChannel.send(slot)
```

## Tasks
- [ ] Create `AlertChannel` abstract base class with `async def send(self, slot: SlotResult) -> None`
- [ ] Create `AlertDispatcher` in `visa_checker/alerts/dispatcher.py`
  - Accepts a list of enabled `AlertChannel` instances
  - `dispatch(slot)` fires all channels concurrently via `asyncio.gather`
  - Catches per-channel `AlertError` and logs without blocking other channels
  - Calls `state.mark_alerted(slot.slot_id)` on success
- [ ] Implement exponential backoff retry (3 attempts) per channel on transient errors
- [ ] Add a `test_all()` method that sends a test message to all channels (used by CLI `test-alerts` command)

## Alert Message Format
```
🟢 VISA SLOT AVAILABLE

Country:  France (Schengen)
Centre:   London - TLScontact
Date:     Tuesday 15 July 2026
Time:     10:30 AM
Provider: TLScontact

Book now: https://...

Detected at: 2026-04-29 14:32 UTC
```

## Acceptance Criteria
- A failure in one channel does not prevent other channels from firing
- `test_all()` sends a recognisable test message through every enabled channel
- `mark_alerted` is only called after at least one channel succeeds
