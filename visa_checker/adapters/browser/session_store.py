"""Session/cookie persistence per provider."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from loguru import logger

_DEFAULT_TTL_HOURS = 4


class SessionStore:
    def __init__(self, sessions_dir: str = "data/sessions", ttl_hours: int = _DEFAULT_TTL_HOURS) -> None:
        self._dir = Path(sessions_dir)
        self._ttl = timedelta(hours=ttl_hours)

    def _path(self, provider: str) -> Path:
        return self._dir / f"{provider}.json"

    def _is_expired(self, saved_at: str) -> bool:
        try:
            ts = datetime.fromisoformat(saved_at)
            return datetime.now(timezone.utc) - ts > self._ttl
        except (ValueError, TypeError):
            return True

    async def load(self, context: Any, provider: str) -> bool:
        """Inject saved cookies into a BrowserContext. Returns True if session was loaded."""
        path = self._path(provider)
        if not path.exists():
            return False

        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return False

        if self._is_expired(data.get("saved_at", "")):
            logger.info("Session for {} has expired, will re-login", provider)
            self.invalidate(provider)
            return False

        await context.add_cookies(data["cookies"])
        logger.info("Loaded session for {} ({} cookies)", provider, len(data["cookies"]))
        return True

    async def save(self, context: Any, provider: str) -> None:
        """Persist current cookies for a BrowserContext."""
        self._dir.mkdir(parents=True, exist_ok=True)
        cookies = await context.cookies()
        data = {
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "cookies": cookies,
        }
        self._path(provider).write_text(json.dumps(data, default=str))
        logger.info("Saved session for {} ({} cookies)", provider, len(cookies))

    def invalidate(self, provider: str) -> None:
        path = self._path(provider)
        if path.exists():
            path.unlink()
            logger.info("Invalidated session for {}", provider)
