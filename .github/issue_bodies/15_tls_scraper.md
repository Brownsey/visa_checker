## Summary
Implement the TLScontact scraper for UK application centres. TLScontact handles Schengen appointments for France, Portugal, Belgium, Denmark, and others.

## Login Flow (tlscontact.com / vcas.tlscontact.com)
1. Navigate to `https://fr.tlscontact.com/gb/lon/` (country-specific subdomain)
2. Click the login/register button
3. Enter email + password
4. Solve hCaptcha via `CaptchaSolver` if presented
5. Submit and wait for the account dashboard
6. Save session cookies

## Slot Check Flow
1. Navigate to the appointment booking section
2. Select visa category (Short Stay Schengen)
3. Request available dates from the calendar widget
4. TLScontact uses an internal AJAX endpoint to return available dates — capture and parse this response
5. For each available date, extract times if available
6. Return list of `SlotResult`

## Tasks
- [ ] Implement `TLSContactScraper(BaseScraper)` in `visa_checker/scrapers/tls_contact.py`
- [ ] Handle country-specific subdomains: `fr`, `pt`, `be`, `dk`
- [ ] Intercept the AJAX calendar endpoint via `page.on("response", ...)` for efficient slot parsing
- [ ] Detect "no appointments available" message and return empty list
- [ ] Handle hCaptcha via `CaptchaSolver`
- [ ] Save sanitised HTML + XHR snapshots to `tests/fixtures/tls_contact/`
- [ ] Write unit tests using fixture data

## Supported Countries (initial)
France, Portugal, Belgium, Denmark, Netherlands

## Acceptance Criteria
- Returns `list[SlotResult]` with valid `booking_url` values linking to the TLS appointment page
- Empty list returned (not an exception) when no slots available
- AJAX response interception works without race conditions
