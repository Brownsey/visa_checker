## Summary
Implement the VFS Global scraper covering UK application centres. VFS Global handles Schengen visa appointments for Germany, Italy, Netherlands, Denmark, Belgium, Czech Republic, and others.

## Login Flow (vfsglobal.com)
1. Navigate to `https://visa.vfsglobal.com/gbr/en/{country}/login`
2. Enter email + password using `human_type`
3. Solve reCAPTCHA v2 via `CaptchaSolver`
4. Submit form, wait for redirect to dashboard
5. Save session cookies

## Slot Check Flow
1. Navigate to the appointment booking page for the target centre
2. Parse the date picker or calendar widget to extract available dates
3. For each available date, extract available times (if shown)
4. Construct booking URL (direct deep-link to the date selection)
5. Return list of `SlotResult`

## Tasks
- [ ] Implement `VFSGlobalScraper(BaseScraper)` in `visa_checker/scrapers/vfs_global.py`
- [ ] Map country names to VFS Global URL slugs (e.g. `Germany` -> `germany`)
- [ ] Handle the "no slots available" page (detect the specific message, return empty list)
- [ ] Handle session expiry: detect login redirect mid-flow and trigger re-login
- [ ] Handle Cloudflare challenge page: detect and raise `ScraperError` with clear message
- [ ] Save sanitised HTML snapshots to `tests/fixtures/vfs_global/` for offline tests
- [ ] Add unit tests using fixture HTML (no live network calls)

## Supported Countries (initial)
Germany, Italy, Netherlands, Denmark, Belgium, Czech Republic, Ireland, Hungary, Latvia

## Acceptance Criteria
- Returns a non-empty `list[SlotResult]` when slots exist on the live site
- Returns empty list (no exception) when no slots are available
- Login is not re-attempted if a valid session cookie exists
- All `SlotResult` objects have a valid `booking_url` that deep-links to the date
