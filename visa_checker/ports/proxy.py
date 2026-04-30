"""Port: proxy provider interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ProxyConfig:
    server: str       # e.g. "http://host:port"
    username: str = ""
    password: str = ""


class IProxyProvider(ABC):
    @abstractmethod
    def next(self) -> ProxyConfig | None:
        """Return the next proxy to use, or None if proxies are disabled."""
