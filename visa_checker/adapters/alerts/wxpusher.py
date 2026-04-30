"""WeChat personal push via WxPusher (free, no business account required)."""
from __future__ import annotations

import httpx
from loguru import logger

from visa_checker.domain.errors import AlertError
from visa_checker.domain.models import SlotResult
from visa_checker.ports.alert import IAlertChannel

_API_URL = "https://wxpusher.zjiecode.com/api/send/message"

_HTML_TEMPLATE = """
<h3>🟢 Visa Slot Available</h3>
<table border="1" cellpadding="6" style="border-collapse:collapse">
  <tr><th>Country</th><td>{country} (Schengen)</td></tr>
  <tr><th>Centre</th><td>{centre}</td></tr>
  <tr><th>Provider</th><td>{provider}</td></tr>
  <tr><th>Date</th><td>{date}</td></tr>
  <tr><th>Time</th><td>{time}</td></tr>
</table>
<p><a href="{url}">Book Now →</a></p>
<p style="color:grey;font-size:12px">Detected: {detected}</p>
"""


class WxPusherChannel(IAlertChannel):
    def __init__(self, app_token: str, uid: str = "", topic_id: str = "") -> None:
        self._app_token = app_token
        self._uid = uid
        self._topic_id = topic_id

    @property
    def channel_name(self) -> str:
        return "wxpusher"

    def _payload(self, content: str, summary: str, content_type: int, url: str = "") -> dict:
        payload: dict = {
            "appToken": self._app_token,
            "content": content,
            "summary": summary,
            "contentType": content_type,  # 1=text, 2=HTML, 3=Markdown
            "uids": [self._uid] if self._uid else [],
            "topicIds": [self._topic_id] if self._topic_id else [],
        }
        if url:
            payload["url"] = url
        return payload

    async def _post(self, payload: dict) -> None:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(_API_URL, json=payload)
        if not resp.is_success:
            raise AlertError(f"WxPusher HTTP error {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        if data.get("code") != 1000:
            raise AlertError(f"WxPusher API error {data.get('code')}: {data.get('msg')}")

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
        summary = f"Visa Slot — {slot.country} {slot.centre} {slot.date.strftime('%d %b')}"
        logger.info("[wxpusher] Sending slot alert: {}", slot.slot_id)
        await self._post(self._payload(html, summary, content_type=2, url=slot.booking_url))

    async def send_test(self) -> None:
        await self._post(self._payload(
            "Visa Checker is running. Alerts are working correctly.",
            "Visa Checker — test",
            content_type=1,
        ))
        logger.info("[wxpusher] Test message sent")
