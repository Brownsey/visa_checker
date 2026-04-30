## Summary
Add the `DiscordConfig` Pydantic model and all config/env documentation needed before the `DiscordChannel` adapter can be implemented. This is a config-only change — no adapter code.

## Files to change

### `visa_checker/config/settings.py`
Add `DiscordConfig` model and extend `AlertsConfig`:

```python
class DiscordConfig(BaseModel):
    enabled: bool = False
    webhook_url: str = ""          # full webhook URL including token
    username: str = "Visa Checker" # display name shown in Discord
    avatar_url: str = ""           # optional avatar override

class AlertsConfig(BaseModel):
    telegram: TelegramConfig = TelegramConfig()
    email: EmailConfig = EmailConfig()
    ntfy: NtfyConfig = NtfyConfig()
    sms: SMSConfig = SMSConfig()
    discord: DiscordConfig = DiscordConfig()   # ← add this
```

### `config/config.example.yaml`
Add section:
```yaml
alerts:
  # ... existing channels ...
  discord:
    enabled: false
    webhook_url: ${DISCORD_WEBHOOK_URL}
    username: "Visa Checker"    # optional display name in Discord
```

### `.env.example`
```
# Discord (optional)
# Create webhook: Server Settings → Integrations → Webhooks → New Webhook → Copy URL
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/123456789/abcdef...
```

## Acceptance criteria
- `DiscordConfig` is importable from `visa_checker.config.settings`
- `AlertsConfig` has a `discord` field defaulting to disabled
- Config round-trips through `load_settings()` without error
- `config.example.yaml` includes the Discord section with inline comments
