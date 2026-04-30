## Summary
Implement structured logging and a consistent error-handling strategy so every component emits useful, filterable output, and crashes are surfaced clearly.

## Tasks
- [ ] Configure `loguru` as the global logger with structured JSON output option for production and human-readable for development
- [ ] Define log levels per component (e.g. scraper DEBUG vs scheduler INFO)
- [ ] Add a `VisaCheckerError` base exception class; define subclasses:
  - `ScraperError` — provider returned unexpected response
  - `CaptchaError` — CAPTCHA solving failed or timed out
  - `ProxyError` — proxy connection failure
  - `AlertError` — notification delivery failure
- [ ] Log every poll attempt with: provider, centre, timestamp, result, duration_ms
- [ ] Log every alert dispatch with: channel, slot details, success/failure
- [ ] Redact secrets (tokens, passwords) in all log output
- [ ] Add log rotation: max 10MB per file, keep last 7 days
- [ ] Write a `log_context` context manager to attach per-request metadata to all log calls within a block

## Acceptance Criteria
- All unhandled exceptions are caught at the top-level scheduler and logged with full traceback
- No secrets appear in any log output
- Log rotation is configured and tested
