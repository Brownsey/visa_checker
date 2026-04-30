## Summary
Integrate a CAPTCHA solving service so the scraper can complete reCAPTCHA v2/v3 and hCaptcha challenges without manual intervention.

## Background
VFS Global uses reCAPTCHA v2 on login. TLScontact uses hCaptcha. Without solving these, the login flow blocks. Third-party solving services (2captcha, AntiCaptcha) use human workers and return a solution token within ~30s for ~$2/1000 solves.

## Tasks
- [ ] Create `CaptchaSolver` abstract base class in `visa_checker/anti_detection/captcha.py`
- [ ] Implement `TwoCaptchaSolver`:
  - Detect reCAPTCHA v2 via `data-sitekey` attribute
  - Detect hCaptcha via `data-hcaptcha-sitekey` attribute
  - POST task to 2captcha API, poll for result (max 120s)
  - Inject solved token via `page.evaluate()`
- [ ] Implement `AntiCaptchaSolver` with same interface
- [ ] Implement `NullCaptchaSolver` — raises `CaptchaError` immediately (use when `captcha.provider: none` to surface the problem clearly)
- [ ] `CaptchaSolver.solve(page) -> str` — detects type, solves, injects, returns token
- [ ] Retry solving up to 3 times on failure before raising `CaptchaError`
- [ ] Track solving cost: log each solve with type, duration, and estimated cost

## Acceptance Criteria
- VFS Global login completes automatically when a reCAPTCHA is presented
- Solving timeout after 120s raises `CaptchaError` (not a hang)
- Cost tracking logs are written to the poll log
