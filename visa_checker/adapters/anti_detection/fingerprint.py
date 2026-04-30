"""Browser fingerprint rotation — cycles through realistic Chrome profiles."""
from __future__ import annotations

import itertools
from dataclasses import dataclass

_PROFILES = [
    {"user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36", "viewport": (1366, 768), "timezone": "Europe/London", "locale": "en-GB", "color_depth": 24},
    {"user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36", "viewport": (1920, 1080), "timezone": "Europe/London", "locale": "en-GB", "color_depth": 24},
    {"user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0", "viewport": (1536, 864), "timezone": "Europe/London", "locale": "en-GB", "color_depth": 24},
    {"user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36", "viewport": (1440, 900), "timezone": "Europe/London", "locale": "en-GB", "color_depth": 30},
    {"user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36", "viewport": (2560, 1600), "timezone": "Europe/London", "locale": "en-GB", "color_depth": 30},
    {"user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36", "viewport": (1280, 800), "timezone": "Europe/London", "locale": "en-GB", "color_depth": 24},
    {"user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36", "viewport": (1600, 900), "timezone": "Europe/London", "locale": "en-GB", "color_depth": 24},
    {"user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36", "viewport": (1920, 1080), "timezone": "Europe/London", "locale": "en-GB", "color_depth": 24},
]


@dataclass
class FingerprintProfile:
    user_agent: str
    viewport: tuple[int, int]
    timezone: str
    locale: str
    color_depth: int


class FingerprintRotator:
    def __init__(self) -> None:
        self._cycle = itertools.cycle(
            [FingerprintProfile(**p) for p in _PROFILES]
        )

    def next(self) -> FingerprintProfile:
        return next(self._cycle)
