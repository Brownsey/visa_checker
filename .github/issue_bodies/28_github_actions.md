## Summary
Add GitHub Actions workflows for CI (tests + linting on every push) and an optional scheduled cloud run (run the checker every 10 minutes using GitHub's free compute).

## Workflows

### 1. CI Workflow (`.github/workflows/ci.yml`)
Triggers: push, pull_request to main

- [ ] Set up Python + Poetry
- [ ] Install dependencies
- [ ] Run `ruff check .`
- [ ] Run `mypy visa_checker/`
- [ ] Run `pytest --cov=visa_checker --cov-fail-under=70`
- [ ] Upload coverage report to Codecov (optional)

### 2. Scheduled Checker (`.github/workflows/scheduled_check.yml`)
Triggers: `schedule: cron: '*/10 * * * *'`

> NOTE: GitHub Actions has a minimum cron interval of 5 minutes and may have up to 10 min delay. This is a free fallback if you don't have a VPS.

- [ ] Checkout repo
- [ ] Set up Python + install dependencies
- [ ] Install Playwright Chromium
- [ ] Run `visa-checker check-now` using secrets for config
- [ ] On slot found: send alert via configured channels
- [ ] Store state between runs using a GitHub Actions cache keyed to `state.db`

### 3. Secrets Setup (document in README)
Required GitHub Secrets for the scheduled checker:
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
- `EMAIL_USER`, `EMAIL_PASS`
- `NTFY_TOPIC`
- `CAPTCHA_API_KEY` (if using 2captcha)
- `VISA_CHECKER_CONFIG_B64` (base64-encoded config.yaml)

## Acceptance Criteria
- CI workflow goes green on a clean push
- Scheduled workflow runs and logs "No new slots" or dispatches alerts
- No secrets appear in workflow logs
