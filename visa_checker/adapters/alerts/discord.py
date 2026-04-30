"""Discord webhook alert channel."""
from __future__ import annotations

import asyncio

import httpx
from loguru import logger

from visa_checker.domain.errors import AlertError
from visa_checker.domain.models import SlotResult
from visa_checker.ports.alert import IAlertChannel

_GREEN = 3066993  # Discord decimal color for green


def _build_payload(slot: SlotResult, username: str, avatar_url: str) -> dict:
    payload: dict = {
        "username": username,
        "embeds": [
            {
                "title": "🟢 Visa Slot Available",
                "color": _GREEN,
                "description": f"[**Book Now →**]({slot.booking_url})",
                "fields": [
                    {"name": "Country",  "value": f"{slot.country} (Schengen)", "inline": True},
                    {"name": "Centre",   "value": slot.centre,                  "inline": True},
                    {"name": "Provider", "value": slot.provider.replace("_", " ").title(), "inline": True},
                    {"name": "Date",     "value": slot.human_date(),            "inline": True},
                    {"name": "Time",     "value": slot.human_time(),            "inline": True},
                ],
                "footer": {
                    "text": f"Detected {slot.checked_at.strftime('%Y-%m-%d %H:%M UTC')}"
                },
            }
        ],
    }
    if avatar_url:
        payload["avatar_url"] = avatar_url
    return payload


class DiscordChannel(IAlertChannel):
    def __init__(self, webhook_url: str, username: str = "Visa Checker", avatar_url: str = "") -> None:
        self._url = webhook_url
        self._username = username
        self._avatar_url = avatar_url

    @property
    def channel_name(self) -> str:
        return "discord"

    async def _post(self, payload: dict) -> None:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(self._url, json=payload)

        if resp.status_code == 429:
            retry_after = float(resp.headers.get("Retry-After", "5"))
            logger.warning("[discord] Rate limited, retrying after {}s", retry_after)
            await asyncio.sleep(retry_after)
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(self._url, json=payload)

        if not resp.is_success:
            raise AlertError(f"Discord webhook error {resp.status_code}: {resp.text[:200]}")

    async def send(self, slot: SlotResult) -> None:
        logger.info("[discord] Sending slot alert: {}", slot.slot_id)
        await self._post(_build_payload(slot, self._username, self._avatar_url))

    async def send_test(self) -> None:
        payload = {
            "username": self._username,
            "embeds": [{"title": "✅ Visa Checker — test message", "color": _GREEN,
                        "description": "Alerts are working correctly."}],
        }
        await self._post(payload)
        logger.info("[discord] Test message sent")
