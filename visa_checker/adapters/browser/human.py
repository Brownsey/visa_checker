"""Human-like interaction helpers for Playwright pages."""
from __future__ import annotations

import asyncio
import math
import random
from dataclasses import dataclass
from typing import Any


@dataclass
class BehaviourConfig:
    """Tune all delays. Set to zero values for fast testing."""
    min_key_delay_ms: int = 50
    max_key_delay_ms: int = 200
    typo_chance: float = 0.05      # 5% chance of a typo per character
    min_action_delay_ms: int = 300
    max_action_delay_ms: int = 1200
    mouse_steps: int = 20


_FAST = BehaviourConfig(
    min_key_delay_ms=0,
    max_key_delay_ms=0,
    typo_chance=0.0,
    min_action_delay_ms=0,
    max_action_delay_ms=0,
    mouse_steps=1,
)


async def human_wait(
    min_ms: int, max_ms: int, cfg: BehaviourConfig | None = None
) -> None:
    lo = min_ms if cfg is None else cfg.min_action_delay_ms
    hi = max_ms if cfg is None else cfg.max_action_delay_ms
    await asyncio.sleep(random.randint(lo, hi) / 1000)


async def human_type(
    page: Any,
    selector: str,
    text: str,
    cfg: BehaviourConfig | None = None,
) -> None:
    """Type text with per-character delays and occasional typo+backspace."""
    c = cfg or BehaviourConfig()
    await page.click(selector)
    for char in text:
        if c.typo_chance > 0 and random.random() < c.typo_chance:
            wrong = random.choice("abcdefghijklmnopqrstuvwxyz")
            await page.keyboard.type(wrong)
            await asyncio.sleep(random.randint(c.min_key_delay_ms, c.max_key_delay_ms) / 1000)
            await page.keyboard.press("Backspace")
            await asyncio.sleep(random.randint(c.min_key_delay_ms, c.max_key_delay_ms) / 1000)
        await page.keyboard.type(char)
        await asyncio.sleep(random.randint(c.min_key_delay_ms, c.max_key_delay_ms) / 1000)


async def human_click(
    page: Any,
    selector: str,
    cfg: BehaviourConfig | None = None,
) -> None:
    """Move mouse in a curved arc to the element before clicking."""
    c = cfg or BehaviourConfig()
    element = await page.query_selector(selector)
    if element is None:
        await page.click(selector)
        return

    box = await element.bounding_box()
    if box is None:
        await page.click(selector)
        return

    target_x = box["x"] + box["width"] / 2 + random.uniform(-5, 5)
    target_y = box["y"] + box["height"] / 2 + random.uniform(-3, 3)

    # Bezier curve from current position
    steps = max(1, c.mouse_steps)
    for i in range(1, steps + 1):
        t = i / steps
        # Simple quadratic Bezier with a random control point
        cx = target_x / 2 + random.uniform(-30, 30)
        cy = target_y / 2 + random.uniform(-30, 30)
        x = (1 - t) ** 2 * 0 + 2 * (1 - t) * t * cx + t ** 2 * target_x
        y = (1 - t) ** 2 * 0 + 2 * (1 - t) * t * cy + t ** 2 * target_y
        await page.mouse.move(x, y)
        await asyncio.sleep(0.01)

    await page.mouse.click(target_x, target_y)


async def random_mouse_movement(page: Any, n: int = 3, cfg: BehaviourConfig | None = None) -> None:
    """Make n random mouse moves to build a realistic trail before interacting."""
    c = cfg or BehaviourConfig()
    vp = page.viewport_size or {"width": 1366, "height": 768}
    for _ in range(n):
        x = random.randint(100, vp["width"] - 100)
        y = random.randint(100, vp["height"] - 100)
        await page.mouse.move(x, y)
        await asyncio.sleep(random.uniform(0.05, 0.2))


async def human_scroll(page: Any, distance: int = 300, cfg: BehaviourConfig | None = None) -> None:
    """Scroll in variable-speed increments."""
    steps = random.randint(3, 8)
    step_size = distance // steps
    for _ in range(steps):
        await page.mouse.wheel(0, step_size + random.randint(-20, 20))
        await asyncio.sleep(random.uniform(0.05, 0.15))
