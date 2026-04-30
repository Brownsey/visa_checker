## Summary
Implement the BLS International scraper for Spain visa appointments from UK application centres (London, Edinburgh, Manchester).

## Target Site
`https://uk.blsspainvisa.com/`

## Login Flow
1. Navigate to the BLS Spain UK portal
2. Register / log in with email and password
3. Navigate to appointment booking section

## Slot Check Flow
1. Select applicant category (short stay Schengen)
2. Select preferred centre (London / Edinburgh / Manchester)
3. Check the appointment calendar for available dates
4. Extract available slots and construct booking URLs

## Tasks
- [ ] Implement `BLSInternationalScraper(BaseScraper)` in `visa_checker/scrapers/bls_international.py`
- [ ] Handle the centre selection flow
- [ ] Parse the appointment calendar (BLS uses a different calendar widget than VFS/TLS)
- [ ] Detect "no slots" state and return empty list
- [ ] Save sanitised HTML fixtures to `tests/fixtures/bls/`
- [ ] Write unit tests using fixture data

## Supported Countries
Spain (initial); Italy possible extension once Spain is stable

## Acceptance Criteria
- Scraper runs against the live BLS portal without triggering a block
- Correctly distinguishes "no slots" from a page load error
- `SlotResult.booking_url` links directly to the BLS appointment booking page
