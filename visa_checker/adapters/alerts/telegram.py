"""Telegram Bot alert channel."""
from __future__ import annotations

import httpx
from loguru import logger

from visa_checker.domain.errors import AlertError
from visa_checker.domain.models import SlotResult
from visa_checker.ports.alert import IAlertChannel

_API = "https://api.telegram.org/bot{token}/{method}"


def _escape(text: str) -> str:
    """Escape Telegram MarkdownV2 special characters."""
    for ch in r"\_*[]()~`>#+-=|{}.!":
        text = text.replace(ch, f"\\{ch}")
    return text


def _format_slot(slot: SlotResult) -> str:
    return (
        f"🟢 *VISA SLOT AVAILABLE*\n\n"
        f"*Country:* {_escape(slot.country)} \\(Schengen\\)\n"
        f"*Centre:* {_escape(slot.centre)} \\- {_escape(slot.provider.replace('_', ' ').title())}\n"
        f"*Date:* {_escape(slot.human_date())}\n"
        f"*Time:* {_escape(slot.human_time())}\n\n"
        f"[Book Now]({slot.booking_url})\n\n"
        f"_Detected: {_escape(slot.checked_at.strftime('%Y-%m-%d %H:%M UTC'))}_"
    )


class TelegramChannel(IAlertChannel):
    def __init__(self, bot_token: str, chat_id: str) -> None:
        self._token = bot_token
        self._chat_id = chat_id

    @property
    def channel_name(self) -> str:
        return "telegram"

    async def _post(self, text: str) -> None:
        url = _API.format(token=self._token, method="sendMessage")
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                url,
                json={
                    "chat_id": self._chat_id,
                    "text": text,
                    "parse_mode": "MarkdownV2",
                    "disable_web_page_preview": False,
                },
            )
        if resp.status_code == 429:
            import asyncio
            retry_after = int(resp.headers.get("Retry-After", "5"))
            logger.warning("[telegram] Rate limited, retrying after {}s", retry_after)
            await asyncio.sleep(retry_after)
            await self._post(text)
            return
        if not resp.is_success:
            raise AlertError(f"Telegram API error {resp.status_code}: {resp.text}")

    async def send(self, slot: SlotResult) -> None:
        logger.info("[telegram] Sending slot alert: {}", slot.slot_id)
        await self._post(_format_slot(slot))

    async def send_test(self) -> None:
        await self._post(
            "✅ *Visa Checker* — test message\\. Alerts are working correctly\\."
        )
        logger.info("[telegram] Test message sent")
