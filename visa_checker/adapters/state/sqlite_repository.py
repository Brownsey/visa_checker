"""SQLite-backed state repository (IStateRepository adapter)."""
from __future__ import annotations

from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any

import aiosqlite

from visa_checker.domain.models import SlotResult
from visa_checker.ports.state import IStateRepository

_SCHEMA = """
CREATE TABLE IF NOT EXISTS slots (
    slot_id      TEXT PRIMARY KEY,
    provider     TEXT NOT NULL,
    country      TEXT NOT NULL,
    centre       TEXT NOT NULL,
    date         TEXT NOT NULL,
    booking_url  TEXT NOT NULL,
    first_seen   TEXT NOT NULL,
    last_seen    TEXT NOT NULL,
    alerted      INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS poll_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    provider     TEXT NOT NULL,
    centre       TEXT NOT NULL,
    checked_at   TEXT NOT NULL,
    slots_found  INTEGER NOT NULL,
    duration_ms  INTEGER NOT NULL,
    error        TEXT
);
"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_slot(row: Any) -> SlotResult:
    return SlotResult(
        provider=row["provider"],
        country=row["country"],
        centre=row["centre"],
        visa_type="short_stay",
        date=date.fromisoformat(row["date"]),
        booking_url=row["booking_url"],
        checked_at=datetime.fromisoformat(row["first_seen"]),
    )


class SQLiteStateRepository(IStateRepository):
    def __init__(self, db_path: str = "data/state.db") -> None:
        self._db_path = Path(db_path)
        self._db: aiosqlite.Connection | None = None

    async def initialise(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self._db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.executescript(_SCHEMA)
        await self._db.commit()

    async def _conn(self) -> aiosqlite.Connection:
        if self._db is None:
            await self.initialise()
        return self._db  # type: ignore[return-value]

    async def is_new(self, slot: SlotResult) -> bool:
        db = await self._conn()
        async with db.execute(
            "SELECT 1 FROM slots WHERE slot_id = ?", (slot.slot_id,)
        ) as cur:
            return await cur.fetchone() is None

    async def mark_seen(self, slot: SlotResult) -> None:
        db = await self._conn()
        now = _now_iso()
        await db.execute(
            """
            INSERT INTO slots (slot_id, provider, country, centre, date, booking_url, first_seen, last_seen)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(slot_id) DO UPDATE SET last_seen = excluded.last_seen
            """,
            (
                slot.slot_id,
                slot.provider,
                slot.country,
                slot.centre,
                slot.date.isoformat(),
                slot.booking_url,
                now,
                now,
            ),
        )
        await db.commit()

    async def mark_alerted(self, slot_id: str) -> None:
        db = await self._conn()
        await db.execute(
            "UPDATE slots SET alerted = 1 WHERE slot_id = ?", (slot_id,)
        )
        await db.commit()

    async def log_poll(
        self,
        provider: str,
        centre: str,
        checked_at: datetime,
        slots_found: int,
        duration_ms: int,
        error: str | None = None,
    ) -> None:
        db = await self._conn()
        await db.execute(
            """
            INSERT INTO poll_log (provider, centre, checked_at, slots_found, duration_ms, error)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (provider, centre, checked_at.isoformat(), slots_found, duration_ms, error),
        )
        await db.commit()

    async def get_history(self, days: int = 7) -> list[SlotResult]:
        db = await self._conn()
        cutoff = datetime.now(timezone.utc)
        # Filter by last_seen within the past N days
        from datetime import timedelta
        cutoff_str = (cutoff - timedelta(days=days)).isoformat()
        async with db.execute(
            "SELECT * FROM slots WHERE last_seen >= ? ORDER BY date ASC",
            (cutoff_str,),
        ) as cur:
            rows = await cur.fetchall()
        return [_row_to_slot(r) for r in rows]

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None
