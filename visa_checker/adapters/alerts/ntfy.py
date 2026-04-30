"""ntfy.sh push notification channel (free, iOS/Android)."""
from __future__ import annotations

import httpx
from loguru import logger

from visa_checker.domain.errors import AlertError
from visa_checker.domain.models import SlotResult
from visa_checker.ports.alert import IAlertChannel


class NtfyChannel(IAlertChannel):
    def __init__(self, topic: str, server: str = "https://ntfy.sh") -> None:
        self._topic = topic
        self._server = server.rstrip("/")

    @property
    def channel_name(self) -> str:
        return "ntfy"

    def _url(self) -> str:
        return f"{self._server}/{self._topic}"

    async def _post(
        self,
        message: str,
        title: str,
        priority: str = "default",
        click_url: str | None = None,
        tags: list[str] | None = None,
    ) -> None:
        headers: dict[str, str] = {
            "Title": title,
            "Priority": priority,
            "Tags": ",".join(tags or []),
        }
        if click_url:
            headers["Click"] = click_url

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(self._url(), content=message.encode(), headers=headers)
        if not resp.is_success:
            raise AlertError(f"ntfy error {resp.status_code}: {resp.text}")

    async def send(self, slot: SlotResult) -> None:
        message = (
            f"{slot.country} (Schengen) – {slot.centre}\n"
            f"Date: {slot.human_date()}\n"
            f"Time: {slot.human_time()}"
        )
        title = f"Visa Slot Available – {slot.country}"
        logger.info("[ntfy] Sending slot alert: {}", slot.slot_id)
        await self._post(
            message,
            title=title,
            priority="urgent",
            click_url=slot.booking_url,
            tags=["airplane", "passport_control"],
        )

    async def send_test(self) -> None:
        await self._post(
            "Visa Checker is running. Alerts are working correctly.",
            title="Visa Checker – Test",
            priority="low",
            tags=["white_check_mark"],
        )
        logger.info("[ntfy] Test notification sent")
