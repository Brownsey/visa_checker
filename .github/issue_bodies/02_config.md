## Summary
Define and validate all user-configurable settings via a YAML file backed by Pydantic v2 models. This is the single source of truth for what countries to watch, what date range to target, and which alert channels are active.

## Configuration Model

```yaml
targets:
  - country: France
    provider: tlscontact
    centre: London
    visa_type: short_stay
    earliest_date: 2026-06-01
    latest_date: 2026-09-30
  - country: Germany
    provider: vfs_global
    centre: London
    visa_type: short_stay
    earliest_date: 2026-06-01
    latest_date: 2026-09-30

polling:
  interval_seconds: 90
  jitter_pct: 0.20   # +/-20% random jitter per poll

alerts:
  telegram:
    enabled: true
    bot_token: ${TELEGRAM_BOT_TOKEN}
    chat_id: ${TELEGRAM_CHAT_ID}
  email:
    enabled: false
    smtp_host: smtp.gmail.com
    smtp_port: 587
    username: ${EMAIL_USER}
    password: ${EMAIL_PASS}
    to: user@example.com
  ntfy:
    enabled: true
    topic: ${NTFY_TOPIC}
  sms:
    enabled: false
    twilio_sid: ${TWILIO_SID}
    twilio_token: ${TWILIO_TOKEN}
    from_number: ${TWILIO_FROM}
    to_number: ${TWILIO_TO}

proxies:
  enabled: false
  provider: brightdata   # brightdata | file
  endpoint: ${PROXY_ENDPOINT}
  file: proxies.txt

captcha:
  provider: 2captcha    # 2captcha | anticaptcha | none
  api_key: ${CAPTCHA_API_KEY}
```

## Tasks
- [ ] Define Pydantic v2 `Settings` model hierarchy matching the YAML above
- [ ] Support `${ENV_VAR}` interpolation inside YAML string values at load time
- [ ] Load config from path passed via CLI or `VISA_CHECKER_CONFIG` env var (default: `config/config.yaml`)
- [ ] Validate date ranges: earliest < latest, not in the past
- [ ] Validate that referenced providers are supported
- [ ] Raise `ConfigValidationError` with clear field paths on failure
- [ ] Ship a fully annotated `config/config.example.yaml`

## Acceptance Criteria
- Invalid config raises `ConfigValidationError` with a human-readable message
- `config.example.yaml` loads without errors
- All secrets can be supplied via environment variables without editing the YAML
