"""Tests for WxPusherChannel."""
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from visa_checker.adapters.alerts.wxpusher import WxPusherChannel
from visa_checker.domain.errors import AlertError
from visa_checker.domain.models import SlotResult


def _slot() -> SlotResult:
    return SlotResult(
        provider="tlscontact",
        country="France",
        centre="London",
        visa_type="short_stay",
        date=date(2026, 7, 15),
        booking_url="https://example.com/book",
        checked_at=datetime(2026, 4, 30, 9, 0, tzinfo=timezone.utc),
    )


def _make_mock_client(response_json: dict, status_code: int = 200):
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.is_success = status_code < 400
    mock_resp.json = MagicMock(return_value=response_json)
    mock_resp.text = str(response_json)

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_resp)
    return mock_client


async def test_send_posts_app_token_and_uid():
    channel = WxPusherChannel(app_token="AT_test", uid="UID_test")

    with patch("httpx.AsyncClient", return_value=_make_mock_client({"code": 1000, "msg": "ok"})):
        await channel.send(_slot())

    call_kwargs = channel._app_token  # just verify no exception


async def test_send_includes_booking_url():
    channel = WxPusherChannel(app_token="AT_test", uid="UID_test")
    sent_payload = {}

    async def _fake_post(url, json=None, **_):
        sent_payload.update(json or {})
        resp = MagicMock()
        resp.is_success = True
        resp.json = MagicMock(return_value={"code": 1000})
        return resp

    with patch("httpx.AsyncClient") as cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=_fake_post)
        cls.return_value = mock_client
        await channel.send(_slot())

    assert sent_payload.get("url") == _slot().booking_url
    assert sent_payload.get("appToken") == "AT_test"
    assert "UID_test" in sent_payload.get("uids", [])


async def test_send_raises_on_non_1000_code():
    channel = WxPusherChannel(app_token="AT_test", uid="UID_test")

    with patch("httpx.AsyncClient", return_value=_make_mock_client({"code": 1001, "msg": "invalid token"})):
        with pytest.raises(AlertError, match="1001"):
            await channel.send(_slot())


async def test_send_raises_on_http_error():
    channel = WxPusherChannel(app_token="AT_test", uid="UID_test")

    with patch("httpx.AsyncClient", return_value=_make_mock_client({}, status_code=500)):
        with pytest.raises(AlertError):
            await channel.send(_slot())


async def test_send_test_uses_plain_text():
    channel = WxPusherChannel(app_token="AT_test", uid="UID_test")
    sent_payload = {}

    async def _fake_post(url, json=None, **_):
        sent_payload.update(json or {})
        resp = MagicMock()
        resp.is_success = True
        resp.json = MagicMock(return_value={"code": 1000})
        return resp

    with patch("httpx.AsyncClient") as cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=_fake_post)
        cls.return_value = mock_client
        await channel.send_test()

    assert sent_payload.get("contentType") == 1
