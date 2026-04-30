"""Tests for WeChatWorkChannel."""
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from visa_checker.adapters.alerts.wechat_work import WeChatWorkChannel, _markdown
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


def test_markdown_contains_booking_url():
    md = _markdown(_slot())
    assert "https://example.com/book" in md


def test_markdown_contains_country():
    md = _markdown(_slot())
    assert "Germany" in md


def test_markdown_contains_date():
    md = _markdown(_slot())
    assert "15 July 2026" in md


def _mock_client(errcode: int = 0):
    mock_resp = MagicMock()
    mock_resp.is_success = True
    mock_resp.json = MagicMock(return_value={"errcode": errcode, "errmsg": "ok" if errcode == 0 else "error"})
    mock_resp.text = ""

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_resp)
    return mock_client


async def test_send_uses_markdown_msgtype():
    channel = WeChatWorkChannel("https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test")
    sent = {}

    async def _fake_post(url, json=None, **_):
        sent.update(json or {})
        resp = MagicMock()
        resp.is_success = True
        resp.json = MagicMock(return_value={"errcode": 0})
        return resp

    with patch("httpx.AsyncClient") as cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=_fake_post)
        cls.return_value = mock_client
        await channel.send(_slot())

    assert sent.get("msgtype") == "markdown"
    assert "markdown" in sent
    assert _slot().booking_url in sent["markdown"]["content"]


async def test_send_includes_mention_mobiles_when_set():
    channel = WeChatWorkChannel(
        "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test",
        mention_mobiles=["+447700900000"],
    )
    sent = {}

    async def _fake_post(url, json=None, **_):
        sent.update(json or {})
        resp = MagicMock()
        resp.is_success = True
        resp.json = MagicMock(return_value={"errcode": 0})
        return resp

    with patch("httpx.AsyncClient") as cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=_fake_post)
        cls.return_value = mock_client
        await channel.send(_slot())

    assert "+447700900000" in sent.get("mentioned_mobile_list", [])


async def test_send_raises_alert_error_on_nonzero_errcode():
    channel = WeChatWorkChannel("https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test")

    with patch("httpx.AsyncClient", return_value=_mock_client(errcode=93000)):
        with pytest.raises(AlertError, match="93000"):
            await channel.send(_slot())


async def test_send_test_uses_text_msgtype():
    channel = WeChatWorkChannel("https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test")
    sent = {}

    async def _fake_post(url, json=None, **_):
        sent.update(json or {})
        resp = MagicMock()
        resp.is_success = True
        resp.json = MagicMock(return_value={"errcode": 0})
        return resp

    with patch("httpx.AsyncClient") as cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=_fake_post)
        cls.return_value = mock_client
        await channel.send_test()

    assert sent.get("msgtype") == "text"
