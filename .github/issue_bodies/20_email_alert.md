## Summary
Implement the email alert channel via SMTP, supporting Gmail (with App Password) and any standard SMTP server.

## Tasks
- [ ] Implement `EmailChannel(AlertChannel)` in `visa_checker/alerts/email.py`
- [ ] Use `aiosmtplib` for async SMTP delivery
- [ ] Support STARTTLS (port 587) and SSL (port 465)
- [ ] Build a clean HTML email template with:
  - Bold slot details table
  - A prominent "Book Now" button linking to the booking URL
  - Plain-text fallback for email clients that don't render HTML
- [ ] Support multiple recipients (`to` field accepts comma-separated list)
- [ ] Handle SMTP authentication errors and connection timeouts gracefully
- [ ] Write unit tests mocking the SMTP connection

## Gmail Setup Note (add to README)
Google requires an "App Password" (not your main password) when 2FA is enabled. Generate one at myaccount.google.com/apppasswords and use it as `EMAIL_PASS`.

## Acceptance Criteria
- Email is delivered to Gmail inbox when using App Password credentials
- HTML email renders correctly with slot details and Book Now button
- `AlertError` is raised on auth failure or connection timeout
