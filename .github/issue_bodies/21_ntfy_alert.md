## Summary
Implement the ntfy.sh push notification channel — a free, self-hostable push notification service that delivers alerts directly to your phone via the ntfy app (iOS/Android).

## Why ntfy
- Completely free (ntfy.sh hosted) or self-hostable
- Native iOS and Android apps with instant push
- No account needed — just pick a unique topic name
- Simple HTTP POST API

## Setup
1. Install the ntfy app on your phone
2. Subscribe to your chosen topic (e.g. `visa-checker-abc123`)
3. Set `NTFY_TOPIC=visa-checker-abc123` in `.env`

## Tasks
- [ ] Implement `NtfyChannel(AlertChannel)` in `visa_checker/alerts/ntfy.py`
- [ ] POST to `https://ntfy.sh/{topic}` (or configurable server URL for self-hosted)
- [ ] Set notification title, priority, tags, and click action (opens booking URL)
- [ ] Use `httpx` for async HTTP POST
- [ ] Set notification priority to `urgent` for slot alerts, `low` for test messages
- [ ] Set the `Click` header to the booking URL so tapping the notification opens the booking page directly
- [ ] Write unit tests mocking the ntfy endpoint

## HTTP Request Example
```
POST https://ntfy.sh/visa-checker-abc123
Title: Visa Slot Available - France
Priority: urgent
Tags: airplane
Click: https://booking-url

France (Schengen) - London TLScontact - 15 Jul 2026 10:30
```

## Acceptance Criteria
- Notification appears on phone within 5 seconds of dispatch
- Tapping the notification opens the booking URL
- Works with a self-hosted ntfy server if `ntfy.server` is configured
