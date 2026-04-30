## Summary
Implement `WxPusherChannel(IAlertChannel)` — pushes slot alerts to a personal WeChat account via the WxPusher API. Wire it into the factory.

**Depends on:** #32 (WxPusherConfig)

## API reference
```
POST https://wxpusher.zjiecode.com/api/send/message
Content-Type: application/json

{
  "appToken": "AT_xxx",
  "content": "<message text or HTML>",
  "summary": "Visa Slot Available — France",   // preview text shown in WeChat notification
  "contentType": 1,                            // 1=text, 2=HTML, 3=Markdown
  "uids": ["UID_xxx"],                         // recipient UIDs
  "topicIds": [],                              // optional topic broadcast
  "url": "https://booking-url"                 // tap-to-open URL
}
```

Response: `{"code": 1000, "msg": "处理成功", "data": [...]}`
Error codes: `1001` = app token invalid, `1002` = UID not found

## Implementation

### `visa_checker/adapters/alerts/wxpusher.py`
- POST JSON to `https://wxpusher.zjiecode.com/api/send/message`
- `contentType: 2` (HTML) for rich formatting with the slot details table
- `summary`: short preview text e.g. `"Visa Slot — France London 15 Jul"`
- `url`: set to `slot.booking_url` so tapping the WeChat notification opens booking page
- Parse response: `code != 1000` → raise `AlertError(msg)`
- `send_test()`: sends `contentType: 1` (plain text) test message

### `visa_checker/application/factory.py`
```python
from visa_checker.adapters.alerts.wxpusher import WxPusherChannel

if a.wxpusher.enabled:
    channels.append(WxPusherChannel(
        app_token=a.wxpusher.app_token,
        uid=a.wxpusher.uid,
        topic_id=a.wxpusher.topic_id,
    ))
```

### `tests/adapters/alerts/test_wxpusher.py`
- Mock POST, assert `appToken` and `uids` in payload
- Assert `url` in payload equals `slot.booking_url`
- Assert `AlertError` raised when response `code != 1000`
- Assert `send_test()` sends plain-text content

## Acceptance criteria
- Message delivered to WeChat within ~5 seconds of `send(slot)` call
- Tapping the WeChat notification opens `slot.booking_url`
- `AlertError` raised (not unhandled exception) on API error codes
- All unit tests pass without network access
