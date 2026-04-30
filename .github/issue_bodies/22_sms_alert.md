## Summary
Implement the Twilio SMS alert channel as a fallback/redundancy channel alongside Telegram and ntfy.

## Tasks
- [ ] Implement `SMSChannel(AlertChannel)` in `visa_checker/alerts/sms.py`
- [ ] Use the Twilio REST API via `httpx` (avoid the Twilio SDK to minimise dependencies)
- [ ] Keep SMS body concise (160 chars): country, centre, date, and shortened booking URL
- [ ] Use `httpx.AsyncClient` with Basic Auth (Twilio SID + token)
- [ ] Handle Twilio error codes gracefully (invalid number, insufficient funds)
- [ ] Write unit tests mocking the Twilio API

## SMS Body Example
```
VISA SLOT: France/London TLScontact 15-Jul-2026 10:30. Book: https://tls.ly/abc123
```

## Acceptance Criteria
- SMS is delivered to the configured `to_number` within 30s
- Error responses from Twilio API raise `AlertError` with the Twilio error code
- SMS body never exceeds 160 characters
