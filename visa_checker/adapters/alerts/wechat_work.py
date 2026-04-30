"""WeChat Work (WeCom) group bot webhook alert channel."""
from __future__ import annotations

import httpx
from loguru import logger

from visa_checker.domain.errors import AlertError
from visa_checker.domain.models import SlotResult
from visa_checker.ports.alert import IAlertChannel


def _markdown(slot: SlotResult) -> str:
    return (
        f"## 🟢 Visa Slot Available\n\n"
        f"> **Country:** {slot.country} (Schengen)\n"
        f"> **Centre:** {slot.centre}\n"
        f"> **Provider:** {slot.provider.replace('_', ' ').title()}\n"
        f"> **Date:** {slot.human_date()}\n"
        f"> **Time:** {slot.human_time()}\n\n"
        f"[Book Now →]({slot.booking_url})\n\n"
        f"<font color=\"comment\">Detected: {slot.checked_at.strftime('%Y-%m-%d %H:%M UTC')}</font>"
    )


class WeChatWorkChannel(IAlertChannel):
    def __init__(self, webhook_url: str, mention_mobiles: list[str] | None = None) -> None:
        self._url = webhook_url
        self._mention_mobiles = mention_mobiles or []

    @property
    def channel_name(self) -> str:
        return "wechat_work"

    async def _post(self, payload: dict) -> None:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(self._url, json=payload)
        if not resp.is_success:
            raise AlertError(f"WeCom HTTP error {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        if data.get("errcode", 0) != 0:
            raise AlertError(f"WeCom API error {data['errcode']}: {data.get('errmsg')}")

    async def send(self, slot: SlotResult) -> None:
        payload: dict = {
            "msgtype": "markdown",
            "markdown": {"content": _markdown(slot)},
        }
        if self._mention_mobiles:
            payload["mentioned_mobile_list"] = self._mention_mobiles
        logger.info("[wechat_work] Sending slot alert: {}", slot.slot_id)
        await self._post(payload)

    async def send_test(self) -> None:
        await self._post({
            "msgtype": "text",
            "text": {"content": "Visa Checker — test OK. Alerts are working correctly."},
        })
        logger.info("[wechat_work] Test message sent")
