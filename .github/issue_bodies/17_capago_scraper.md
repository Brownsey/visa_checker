## Summary
Implement the Capago scraper for Finnish and Icelandic Schengen visa appointments from the UK.

## Target Site
`https://www.capago.eu/` (UK bookings for Finland, Iceland)

## Tasks
- [ ] Implement `CapagoScraper(BaseScraper)` in `visa_checker/scrapers/capago.py`
- [ ] Authenticate with Capago portal
- [ ] Navigate to the appointment slot availability calendar
- [ ] Extract available dates and times
- [ ] Return normalised `list[SlotResult]`
- [ ] Save HTML fixtures and write unit tests

## Acceptance Criteria
- Scraper returns slots or empty list without raising on normal site behaviour
- `booking_url` links to the relevant Capago booking page
