"""Twilio SMS alert channel."""
from __future__ import annotations

import httpx
from loguru import logger

from visa_checker.domain.errors import AlertError
from visa_checker.domain.models import SlotResult
from visa_checker.ports.alert import IAlertChannel

_TWILIO_API = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"


class SMSChannel(IAlertChannel):
    def __init__(self, twilio_sid: str, twilio_token: str, from_number: str, to_number: str) -> None:
        self._sid = twilio_sid
        self._token = twilio_token
        self._from = from_number
        self._to = to_number

    @property
    def channel_name(self) -> str:
        return "sms"

    async def _send_sms(self, body: str) -> None:
        # Truncate to 160 chars
        body = body[:160]
        url = _TWILIO_API.format(sid=self._sid)
        async with httpx.AsyncClient(timeout=15, auth=(self._sid, self._token)) as client:
            resp = await client.post(
                url,
                data={"From": self._from, "To": self._to, "Body": body},
            )
        if not resp.is_success:
            raise AlertError(f"Twilio error {resp.status_code}: {resp.text[:200]}")

    async def send(self, slot: SlotResult) -> None:
        body = (
            f"VISA SLOT: {slot.country}/{slot.centre} "
            f"{slot.date.strftime('%d-%b-%Y')} {slot.human_time()}. "
            f"Book: {slot.booking_url}"
        )
        logger.info("[sms] Sending slot alert: {}", slot.slot_id)
        await self._send_sms(body)

    async def send_test(self) -> None:
        await self._send_sms("Visa Checker test: alerts are working correctly.")
        logger.info("[sms] Test SMS sent")
