## Summary
Persist seen slots in a local SQLite database so the system only alerts on newly appeared slots, not every slot on every poll.

## Schema

```sql
CREATE TABLE slots (
    slot_id      TEXT PRIMARY KEY,
    provider     TEXT NOT NULL,
    country      TEXT NOT NULL,
    centre       TEXT NOT NULL,
    date         TEXT NOT NULL,
    booking_url  TEXT NOT NULL,
    first_seen   TEXT NOT NULL,   -- ISO-8601 UTC
    last_seen    TEXT NOT NULL,   -- ISO-8601 UTC
    alerted      INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE poll_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    provider     TEXT NOT NULL,
    centre       TEXT NOT NULL,
    checked_at   TEXT NOT NULL,
    slots_found  INTEGER NOT NULL,
    duration_ms  INTEGER NOT NULL,
    error        TEXT
);
```

## Tasks
- [ ] Implement `StateManager` class backed by `aiosqlite`
- [ ] `StateManager.is_new(slot: SlotResult) -> bool` — returns True if slot_id not yet seen
- [ ] `StateManager.mark_seen(slot: SlotResult)` — upsert into `slots` table
- [ ] `StateManager.mark_alerted(slot_id: str)` — set `alerted=1`
- [ ] `StateManager.log_poll(...)` — insert row into `poll_log`
- [ ] `StateManager.get_history(days=7) -> list[SlotResult]` — query recent history
- [ ] Database path configurable via config (default: `data/state.db`)
- [ ] Auto-migrate schema on first run
- [ ] Unit tests with in-memory SQLite

## Acceptance Criteria
- Same slot seen twice: `is_new` returns True first time, False second time
- All operations are async-safe and work under concurrent poll tasks
- Database schema is created automatically on first run
