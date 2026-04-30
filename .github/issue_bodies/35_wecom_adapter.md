## Summary
Implement `WeChatWorkChannel(IAlertChannel)` — posts Markdown-formatted slot alerts to a WeCom group chat bot webhook. Wire it into the factory.

**Depends on:** #34 (WeChatWorkConfig)

## API reference
```
POST https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY
Content-Type: application/json

{
  "msgtype": "markdown",
  "markdown": {
    "content": "## 🟢 Visa Slot Available\n> **Country:** France (Schengen)\n..."
  }
}
```

WeCom Markdown supports: `**bold**`, `> blockquote`, `[link](url)`, `<font color=\"info\">text</font>` (info=blue, warning=yellow, comment=grey).

To @mention members: add `mentioned_mobile_list` at the top level alongside `markdown`.

Response: `{"errcode": 0, "errmsg": "ok"}` — any non-zero `errcode` is a failure.

## Implementation

### `visa_checker/adapters/alerts/wechat_work.py`

Message format:
```
## 🟢 Visa Slot Available

**Country:** France (Schengen)
**Centre:** London — TLScontact
**Date:** Wednesday 15 July 2026
**Time:** 10:30 AM

[Book Now](https://booking-url)

<font color="comment">Detected: 2026-04-30 09:15 UTC</font>
```

- Build POST payload with `msgtype: "markdown"` and the formatted string
- If `mention_mobiles` is non-empty, add `"mentioned_mobile_list"` field alongside `"markdown"`
- Parse response: `errcode != 0` → raise `AlertError(f"WeCom error {errcode}: {errmsg}")`
- `send_test()`: sends a plain `text` message type: `{"msgtype":"text","text":{"content":"Visa Checker — test OK"}}`

### `visa_checker/application/factory.py`
```python
from visa_checker.adapters.alerts.wechat_work import WeChatWorkChannel

if a.wechat_work.enabled:
    channels.append(WeChatWorkChannel(
        webhook_url=a.wechat_work.webhook_url,
        mention_mobiles=a.wechat_work.mention_mobiles,
    ))
```

### `tests/adapters/alerts/test_wechat_work.py`
- Mock POST, assert `msgtype == "markdown"` in payload
- Assert `booking_url` appears in `markdown.content`
- Assert `mentioned_mobile_list` present when `mention_mobiles` is non-empty
- Assert `AlertError` raised on `errcode != 0`
- Assert `send_test()` uses `msgtype == "text"`

## Acceptance criteria
- Message appears in WeCom group chat within seconds of `send(slot)` call
- Markdown renders correctly (bold fields, clickable Book Now link)
- `mention_mobiles` triggers `@mention` in the group message
- `AlertError` raised (not unhandled) on API error response
- All unit tests pass without network access
