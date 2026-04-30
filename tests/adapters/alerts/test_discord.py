"""Tests for DiscordChannel."""
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from visa_checker.adapters.alerts.discord import DiscordChannel, _GREEN, _build_payload
from visa_checker.domain.errors import AlertError
from visa_checker.domain.models import SlotResult


def _slot() -> SlotResult:
    return SlotResult(
        provider="vfs_global",
        country="Germany",
        centre="London",
        visa_type="short_stay",
        date=date(2026, 7, 15),
        booking_url="https://example.com/book",
        checked_at=datetime(2026, 4, 30, 9, 0, tzinfo=timezone.utc),
    )


def test_build_payload_color_is_green():
    slot = _slot()
    payload = _build_payload(slot, "Visa Checker", "")
    assert payload["embeds"][0]["color"] == _GREEN


def test_build_payload_booking_url_in_description():
    slot = _slot()
    payload = _build_payload(slot, "Visa Checker", "")
    assert slot.booking_url in payload["embeds"][0]["description"]


def test_build_payload_username():
    slot = _slot()
    payload = _build_payload(slot, "My Bot", "")
    assert payload["username"] == "My Bot"


def test_build_payload_avatar_url_omitted_when_empty():
    slot = _slot()
    payload = _build_payload(slot, "Visa Checker", "")
    assert "avatar_url" not in payload


def test_build_payload_avatar_url_included_when_set():
    slot = _slot()
    payload = _build_payload(slot, "Visa Checker", "https://example.com/avatar.png")
    assert payload["avatar_url"] == "https://example.com/avatar.png"


def test_build_payload_fields_include_country_and_date():
    slot = _slot()
    payload = _build_payload(slot, "Visa Checker", "")
    field_names = [f["name"] for f in payload["embeds"][0]["fields"]]
    assert "Country" in field_names
    assert "Date" in field_names


async def test_send_posts_to_webhook():
    channel = DiscordChannel("https://discord.com/api/webhooks/123/abc")
    mock_resp = MagicMock()
    mock_resp.status_code = 204
    mock_resp.is_success = True

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        await channel.send(_slot())
        mock_client.post.assert_awaited_once()
        _, kwargs = mock_client.post.call_args
        assert "embeds" in kwargs["json"]


async def test_send_raises_alert_error_on_4xx():
    channel = DiscordChannel("https://discord.com/api/webhooks/123/abc")
    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.is_success = False
    mock_resp.text = "Bad Request"

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        with pytest.raises(AlertError):
            await channel.send(_slot())


async def test_send_retries_on_429():
    channel = DiscordChannel("https://discord.com/api/webhooks/123/abc")
    rate_limited = MagicMock(status_code=429, is_success=False)
    rate_limited.headers = {"Retry-After": "0"}
    ok = MagicMock(status_code=204, is_success=True)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=[rate_limited, ok])
        mock_client_cls.return_value = mock_client

        with patch("asyncio.sleep", new_callable=AsyncMock):
            await channel.send(_slot())

        assert mock_client.post.await_count == 2
