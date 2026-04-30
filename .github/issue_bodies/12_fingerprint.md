## Summary
Rotate browser fingerprints (user agent, screen resolution, timezone, language) across browser sessions to reduce the chance of fingerprint-based bot detection.

## Background
Sites like VFS Global track browser fingerprints across sessions. If every request comes from the same `Chrome/131 Windows` / `1366x768` / `en-GB` combination, it becomes a detection signal. Rotating these within realistic bounds makes the traffic look like different users.

## Tasks
- [ ] Create `FingerprintProfile` dataclass in `visa_checker/anti_detection/fingerprint.py`
  - `user_agent: str`
  - `viewport: tuple[int, int]`
  - `timezone: str` (e.g. "Europe/London")
  - `locale: str` (e.g. "en-GB")
  - `color_depth: int` (24 or 32)
- [ ] Maintain a curated list of ~20 realistic Windows/Mac Chrome profiles
- [ ] `FingerprintRotator.next() -> FingerprintProfile` — returns the next profile, cycling through the list
- [ ] Apply profile when creating a new browser context:
  - `context.set_extra_http_headers({"Accept-Language": locale})`
  - `context.set_viewport_size(...)`
  - Inject timezone via `page.emulate_timezone()`
  - Set `navigator.language` via stealth patch
- [ ] A new fingerprint is chosen at the start of each full scraper run (not per page)

## Acceptance Criteria
- Two consecutive scraper runs produce different `navigator.userAgent` values
- Viewport, timezone, and locale all match the selected profile
- All profiles are valid Chrome/Windows or Chrome/Mac combinations
