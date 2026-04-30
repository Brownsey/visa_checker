"""Alert dispatcher — fans out new slot notifications to all configured channels."""
from __future__ import annotations

import asyncio

from loguru import logger

from visa_checker.domain.errors import AlertError
from visa_checker.domain.models import SlotResult
from visa_checker.ports.alert import IAlertChannel
from visa_checker.ports.state import IStateRepository

_MAX_RETRIES = 3
_RETRY_BASE = 2.0


async def _send_with_retry(channel: IAlertChannel, slot: SlotResult) -> bool:
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            await channel.send(slot)
            return True
        except AlertError as exc:
            if attempt < _MAX_RETRIES:
                wait = _RETRY_BASE ** attempt
                logger.warning(
                    "[{}] Alert failed (attempt {}/{}), retrying in {}s: {}",
                    channel.channel_name, attempt, _MAX_RETRIES, wait, exc,
                )
                await asyncio.sleep(wait)
            else:
                logger.error(
                    "[{}] Alert failed after {} attempts: {}",
                    channel.channel_name, _MAX_RETRIES, exc,
                )
    return False


class AlertDispatcher:
    def __init__(
        self,
        channels: list[IAlertChannel],
        state: IStateRepository,
    ) -> None:
        self._channels = channels
        self._state = state

    async def dispatch(self, slot: SlotResult) -> None:
        """Fire all channels concurrently; mark alerted if at least one succeeds."""
        if not self._channels:
            logger.warning("No alert channels configured — slot not dispatched: {}", slot.slot_id)
            return

        results = await asyncio.gather(
            *[_send_with_retry(ch, slot) for ch in self._channels],
            return_exceptions=True,
        )

        successes = sum(1 for r in results if r is True)
        if successes > 0:
            await self._state.mark_alerted(slot.slot_id)
            logger.info("Alert dispatched to {}/{} channels for {}", successes, len(self._channels), slot.slot_id)
        else:
            logger.error("All alert channels failed for slot {}", slot.slot_id)

    async def test_all(self) -> dict[str, bool]:
        """Send test messages to all channels. Returns {channel_name: success}."""
        results: dict[str, bool] = {}
        for channel in self._channels:
            try:
                await channel.send_test()
                results[channel.channel_name] = True
                logger.info("[{}] Test message sent successfully", channel.channel_name)
            except Exception as exc:
                results[channel.channel_name] = False
                logger.error("[{}] Test message failed: {}", channel.channel_name, exc)
        return results
