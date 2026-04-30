"""Structured logging configuration using loguru."""
from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from loguru import logger

_SECRET_PATTERNS = [
    "password",
    "token",
    "api_key",
    "twilio_token",
    "bot_token",
]


def _redact(record: dict) -> bool:
    msg = record["message"].lower()
    for pattern in _SECRET_PATTERNS:
        if pattern in msg:
            record["message"] = "[REDACTED – contains sensitive field]"
            return True
    return True


def configure_logging(level: str = "INFO", log_file: str | None = None) -> None:
    """Set up loguru with console + optional rotating file output."""
    logger.remove()

    logger.add(
        sys.stderr,
        level=level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{line}</cyan> – {message}",
        filter=_redact,
        colorize=True,
        backtrace=True,
        diagnose=False,
    )

    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            log_file,
            level=level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{line} – {message}",
            filter=_redact,
            rotation="10 MB",
            retention="7 days",
            compression="zip",
            backtrace=True,
            diagnose=False,
        )


@contextmanager
def log_context(**kwargs: object) -> Generator[None, None, None]:
    """Attach extra key=value pairs to every log call within the block."""
    with logger.contextualize(**kwargs):
        yield
