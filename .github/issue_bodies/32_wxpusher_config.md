## Summary
Add `WxPusherConfig` to the settings layer. WxPusher is a free service that delivers messages directly to a personal WeChat account — no WeChat business registration required.

## Setup (document in config comments)
1. Visit https://wxpusher.zjiecode.com and log in with WeChat scan
2. Create an application → copy the `APP_TOKEN`
3. In WeChat, follow the WxPusher official account, tap "My UID" → copy your `UID`
4. That's it — no approval process, works globally including UK

## Files to change

### `visa_checker/config/settings.py`
```python
class WxPusherConfig(BaseModel):
    enabled: bool = False
    app_token: str = ""   # from WxPusher dashboard after creating an app
    uid: str = ""         # your personal UID from the WxPusher WeChat menu
    # Optional: send to a topic instead of a UID (for broadcasting to subscribers)
    topic_id: str = ""

class AlertsConfig(BaseModel):
    # ... existing ...
    wxpusher: WxPusherConfig = WxPusherConfig()
```

### `config/config.example.yaml`
```yaml
alerts:
  wxpusher:
    enabled: false
    app_token: ${WXPUSHER_APP_TOKEN}
    uid: ${WXPUSHER_UID}
    # topic_id: ${WXPUSHER_TOPIC_ID}  # alternative: broadcast to topic subscribers
```

### `.env.example`
```
# WeChat via WxPusher (free personal push, no business account needed)
# Setup: https://wxpusher.zjiecode.com — scan QR to register, copy APP_TOKEN + UID
WXPUSHER_APP_TOKEN=AT_xxxxxxxxxxxxxxxx
WXPUSHER_UID=UID_xxxxxxxxxxxxxxxx
```

## Acceptance criteria
- `WxPusherConfig` is importable from `visa_checker.config.settings`
- `AlertsConfig.wxpusher` defaults to disabled
- Config round-trips through `load_settings()` without validation errors
