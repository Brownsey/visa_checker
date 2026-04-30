"""Email alert channel via async SMTP."""
from __future__ import annotations

import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib
from loguru import logger

from visa_checker.domain.errors import AlertError
from visa_checker.domain.models import SlotResult
from visa_checker.ports.alert import IAlertChannel

_HTML_TEMPLATE = """
<html><body style="font-family:sans-serif;max-width:600px;margin:auto">
<h2 style="color:#2e7d32">🟢 Visa Slot Available</h2>
<table style="border-collapse:collapse;width:100%">
  <tr><td style="padding:8px;border:1px solid #ddd"><b>Country</b></td>
      <td style="padding:8px;border:1px solid #ddd">{country} (Schengen)</td></tr>
  <tr><td style="padding:8px;border:1px solid #ddd"><b>Centre</b></td>
      <td style="padding:8px;border:1px solid #ddd">{centre} – {provider}</td></tr>
  <tr><td style="padding:8px;border:1px solid #ddd"><b>Date</b></td>
      <td style="padding:8px;border:1px solid #ddd">{date}</td></tr>
  <tr><td style="padding:8px;border:1px solid #ddd"><b>Time</b></td>
      <td style="padding:8px;border:1px solid #ddd">{time}</td></tr>
</table>
<br>
<a href="{url}" style="background:#1976d2;color:#fff;padding:12px 24px;
   text-decoration:none;border-radius:4px;display:inline-block">Book Now</a>
<p style="color:#888;font-size:12px">Detected: {detected}</p>
</body></html>
"""


class EmailChannel(IAlertChannel):
    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        to: str,
    ) -> None:
        self._host = smtp_host
        self._port = smtp_port
        self._username = username
        self._password = password
        self._to = to

    @property
    def channel_name(self) -> str:
        return "email"

    async def _send_email(self, subject: str, html: str, plain: str) -> None:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self._username
        msg["To"] = self._to
        msg.attach(MIMEText(plain, "plain"))
        msg.attach(MIMEText(html, "html"))

        try:
            await aiosmtplib.send(
                msg,
                hostname=self._host,
                port=self._port,
                username=self._username,
                password=self._password,
                start_tls=self._port == 587,
                use_tls=self._port == 465,
                timeout=30,
            )
        except Exception as exc:
            raise AlertError(f"Email delivery failed: {exc}") from exc

    async def send(self, slot: SlotResult) -> None:
        html = _HTML_TEMPLATE.format(
            country=slot.country,
            centre=slot.centre,
            provider=slot.provider.replace("_", " ").title(),
            date=slot.human_date(),
            time=slot.human_time(),
            url=slot.booking_url,
            detected=slot.checked_at.strftime("%Y-%m-%d %H:%M UTC"),
        )
        plain = (
            f"Visa Slot Available: {slot.country} (Schengen)\n"
            f"Centre: {slot.centre}\nDate: {slot.human_date()}\n"
            f"Book: {slot.booking_url}"
        )
        logger.info("[email] Sending slot alert: {}", slot.slot_id)
        await self._send_email(f"Visa Slot Available – {slot.country} {slot.human_date()}", html, plain)

    async def send_test(self) -> None:
        await self._send_email(
            "Visa Checker – Test Alert",
            "<p>Visa Checker is running correctly. Alerts are working.</p>",
            "Visa Checker is running correctly.",
        )
        logger.info("[email] Test email sent")
