## Summary
Build a Playwright-based browser engine with stealth patches applied so the automation is not detected as a bot by Cloudflare, VFS Global, or TLScontact.

## Background
VFS Global and TLScontact use Cloudflare Bot Management and custom JS fingerprinting. Standard Playwright is trivially detectable via `navigator.webdriver`, missing plugins, and headless Chrome UA strings. The stealth layer patches these.

## Tasks
- [ ] Create `BrowserEngine` class in `visa_checker/browser/engine.py`
- [ ] Integrate `playwright-stealth` (Python port) to patch:
  - `navigator.webdriver` → undefined
  - Chrome plugins / mimeTypes population
  - `window.chrome` object injection
  - Realistic `navigator.languages`, `navigator.platform`
- [ ] Launch with a realistic user-agent (latest stable Chrome on Windows 10)
- [ ] Support headless and headed mode (headed useful for debugging / manual CAPTCHA solving)
- [ ] Implement `async with BrowserEngine() as engine` context manager
- [ ] Expose `engine.new_page(proxy=None)` returning a stealthy `Page`
- [ ] Load cookies from a JSON file on startup (if exists) and save on teardown
- [ ] Set realistic viewport: 1366x768
- [ ] Add random startup delay (1–3s) before any navigation

## Acceptance Criteria
- Visiting https://bot.sannysoft.com/ in headed mode shows no red flags
- `navigator.webdriver` is `undefined` in the page context
- Context manager cleans up browser processes on exit
