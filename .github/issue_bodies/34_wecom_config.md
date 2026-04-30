## Summary
Add `WeChatWorkConfig` for WeChat Work (WeCom) group bot webhooks. WeCom is the enterprise version of WeChat with a simple webhook API — if you use WeChat Work for anything, this is the easiest WeChat option with zero extra registration.

## Setup (document in config comments)
1. Open WeChat Work on desktop or web
2. Open any group chat → right-click → "Add Group Robot" → "Create a bot"
3. Name it "Visa Checker" → confirm → copy the webhook URL
4. Paste it as `WECOM_WEBHOOK_URL` in `.env`

## Files to change

### `visa_checker/config/settings.py`
```python
class WeChatWorkConfig(BaseModel):
    enabled: bool = False
    webhook_url: str = ""   # full URL: https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=...
    # mention_mobiles: list of phone numbers to @mention in the message (optional)
    mention_mobiles: list[str] = []

class AlertsConfig(BaseModel):
    # ... existing ...
    wechat_work: WeChatWorkConfig = WeChatWorkConfig()
```

### `config/config.example.yaml`
```yaml
alerts:
  wechat_work:
    enabled: false
    webhook_url: ${WECOM_WEBHOOK_URL}
    # mention_mobiles: ["+447700900000"]  # optional: @mention someone in the group
```

### `.env.example`
```
# WeChat Work (WeCom) group bot
# Setup: WeChat Work group → right-click → Add Group Robot → Create → copy URL
WECOM_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

## Acceptance criteria
- `WeChatWorkConfig` importable from `visa_checker.config.settings`
- `AlertsConfig.wechat_work` defaults to disabled
- `mention_mobiles` defaults to empty list (no mentions)
- Config round-trips through `load_settings()` without error
