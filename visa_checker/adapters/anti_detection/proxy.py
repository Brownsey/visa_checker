"""Proxy provider adapters.

File format for proxies.txt (one per line, lines starting with # are ignored):
  host:port
  host:port:username:password
  http://host:port
  http://username:password@host:port
"""
from __future__ import annotations

import asyncio
import itertools
import random
import re
from pathlib import Path

import httpx
from loguru import logger

from visa_checker.domain.errors import ProxyError
from visa_checker.ports.proxy import IProxyProvider, ProxyConfig

_HEALTH_URL = "https://httpbin.org/ip"
_HEALTH_TIMEOUT = 8.0

# Parse http://user:pass@host:port or http://host:port
_URL_RE = re.compile(
    r"^(?:https?://)?(?:(?P<user>[^:@]+):(?P<pass>[^@]+)@)?(?P<host>[^:/@]+):(?P<port>\d+)$"
)


def _parse_proxy_line(line: str) -> ProxyConfig | None:
    line = line.strip()
    if not line or line.startswith("#"):
        return None

    # Try URL-style first
    m = _URL_RE.match(line)
    if m:
        host, port = m.group("host"), m.group("port")
        user = m.group("user") or ""
        password = m.group("pass") or ""
        return ProxyConfig(server=f"http://{host}:{port}", username=user, password=password)

    # Fall back to colon-delimited host:port[:user[:pass]]
    parts = line.split(":")
    if len(parts) >= 2:
        host, port = parts[0], parts[1]
        user = parts[2] if len(parts) > 2 else ""
        password = parts[3] if len(parts) > 3 else ""
        return ProxyConfig(server=f"http://{host}:{port}", username=user, password=password)

    return None


async def _check_proxy(proxy: ProxyConfig) -> bool:
    """Return True if the proxy can reach httpbin within the timeout."""
    proxies: dict[str, str] = {
        "http://": proxy.server,
        "https://": proxy.server,
    }
    if proxy.username:
        from httpx import URL

        url = URL(proxy.server)
        auth_server = f"http://{proxy.username}:{proxy.password}@{url.host}:{url.port}"
        proxies = {"http://": auth_server, "https://": auth_server}

    try:
        async with httpx.AsyncClient(proxies=proxies, timeout=_HEALTH_TIMEOUT) as client:  # type: ignore[arg-type]
            resp = await client.get(_HEALTH_URL)
            return resp.is_success
    except Exception:
        return False


class NullProxyProvider(IProxyProvider):
    """No-op — used when proxies are disabled (the default)."""

    def next(self) -> None:
        return None


class FileProxyProvider(IProxyProvider):
    """Randomly selects a proxy from proxies.txt; marks failed proxies and skips them.

    - Default: disabled (NullProxyProvider is used unless proxies.enabled=true in config)
    - Selection: random, not round-robin
    - Failure handling: failed proxies are removed from the pool; pool resets when empty
    - Optional async health-check at startup via validate_all()
    """

    def __init__(self, file_path: str) -> None:
        self._file_path = file_path
        self._all: list[ProxyConfig] = []
        self._active: list[ProxyConfig] = []
        self._failed: set[str] = set()  # failed proxy server strings
        self._load()

    def _load(self) -> None:
        path = Path(self._file_path)
        if not path.exists():
            logger.warning("proxies.txt not found at {}", self._file_path)
            return

        for line in path.read_text(encoding="utf-8").splitlines():
            proxy = _parse_proxy_line(line)
            if proxy:
                self._all.append(proxy)

        self._active = list(self._all)
        logger.info("Loaded {} proxy/proxies from {}", len(self._active), self._file_path)

    def mark_failed(self, server: str) -> None:
        """Remove a proxy from the active pool. Called by the scraper on connection failure."""
        self._failed.add(server)
        self._active = [p for p in self._active if p.server not in self._failed]
        logger.warning(
            "Proxy {} marked as failed. {} proxy/proxies remaining.", server, len(self._active)
        )
        if not self._active:
            logger.warning("All proxies exhausted — resetting pool to full list")
            self._failed.clear()
            self._active = list(self._all)

    def next(self) -> ProxyConfig | None:
        if not self._active:
            return None
        chosen = random.choice(self._active)
        logger.debug("Selected proxy: {}", chosen.server)
        return chosen

    async def validate_all(self) -> int:
        """Health-check all proxies concurrently and remove invalid ones.

        Returns the number of valid proxies remaining.
        """
        if not self._active:
            return 0

        logger.info("Validating {} proxy/proxies…", len(self._active))

        results = await asyncio.gather(
            *[_check_proxy(p) for p in self._active],
            return_exceptions=True,
        )

        valid: list[ProxyConfig] = []
        for proxy, ok in zip(self._active, results):
            if ok is True:
                valid.append(proxy)
            else:
                reason = ok if isinstance(ok, Exception) else "failed health check"
                logger.warning("Proxy {} removed: {}", proxy.server, reason)
                self._failed.add(proxy.server)

        self._active = valid
        logger.info("{}/{} proxies passed validation", len(valid), len(self._all))
        return len(valid)


class BrightDataProxyProvider(IProxyProvider):
    """Generates BrightData sticky-session proxy URLs."""

    def __init__(self, endpoint: str) -> None:
        self._endpoint = endpoint
        self._counter = itertools.count(1)

    def next(self) -> ProxyConfig:
        session_id = next(self._counter)
        return ProxyConfig(server=f"{self._endpoint}-session-{session_id}")


def build_proxy_provider(config: object) -> IProxyProvider:
    """Factory — returns NullProxyProvider when proxies.enabled=false (the default)."""
    from visa_checker.config.settings import ProxiesConfig

    cfg: ProxiesConfig = config  # type: ignore[assignment]
    if not cfg.enabled:
        return NullProxyProvider()
    if cfg.provider == "brightdata":
        return BrightDataProxyProvider(cfg.endpoint)
    return FileProxyProvider(cfg.file)
