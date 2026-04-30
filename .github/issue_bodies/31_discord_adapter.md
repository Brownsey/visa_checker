## Summary
Implement `DiscordChannel(IAlertChannel)` — sends a rich embed to a Discord webhook when a visa slot is found. Wire it into the alert factory so it activates when `alerts.discord.enabled: true`.

**Depends on:** #30 (DiscordConfig model)

## Implementation

### `visa_checker/adapters/alerts/discord.py`

Discord webhooks accept a JSON payload. Use an embed for rich formatting:

```python
payload = {
    "username": config.username,
    "embeds": [{
        "title": "🟢 Visa Slot Available",
        "color": 3066993,  # green (decimal, not hex)
        "fields": [
            {"name": "Country",  "value": f"{slot.country} (Schengen)", "inline": True},
            {"name": "Centre",   "value": slot.centre,                  "inline": True},
            {"name": "Provider", "value": slot.provider,                "inline": True},
            {"name": "Date",     "value": slot.human_date(),            "inline": True},
            {"name": "Time",     "value": slot.human_time(),            "inline": True},
        ],
        "description": f"[**Book Now →**]({slot.booking_url})",
        "footer": {"text": f"Detected {slot.checked_at.strftime('%Y-%m-%d %H:%M UTC')}"},
    }]
}
```

- Use `httpx.AsyncClient` for the POST
- Handle Discord rate limits: HTTP 429 → back off `retry_after` seconds and retry once
- Raise `AlertError` on permanent failures (4xx other than 429, connection error)
- `send_test()` sends an embed with title "✅ Visa Checker — test message"

### `visa_checker/application/factory.py`
```python
from visa_checker.adapters.alerts.discord import DiscordChannel

# inside build_alert_channels():
if a.discord.enabled:
    channels.append(DiscordChannel(a.discord.webhook_url, a.discord.username))
```

### `tests/adapters/alerts/test_discord.py`
- Mock `httpx.AsyncClient.post` to return 200, assert payload shape
- Assert embed color is `3066993` (green)
- Assert `booking_url` appears in `description`
- Mock 429 → assert retry after `Retry-After` header value
- Assert `AlertError` raised on 404

## Acceptance criteria
- `visa-checker test-alerts` delivers a green embed to the configured Discord channel
- Rate-limit (429) causes exactly one retry
- Disabled channel (`enabled: false`) adds no entry to `build_alert_channels()` output
- All unit tests pass without network access
