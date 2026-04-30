## Summary
Create a Dockerfile that bundles Python, Playwright, all Chromium dependencies, and the visa_checker application into a single portable container for 24/7 deployment on any Linux server or VPS.

## Requirements
- Based on `mcr.microsoft.com/playwright/python:v1.x-jammy` (includes all Playwright browser dependencies)
- Minimal image size: use Poetry with `--no-dev` install
- Non-root user for security
- Chromium browser only (no Firefox/WebKit) to reduce image size
- Build arg `PLAYWRIGHT_VERSION` to pin the Playwright version

## Tasks
- [ ] Write multi-stage `Dockerfile`:
  - Stage 1 (builder): install Poetry, export requirements.txt
  - Stage 2 (runtime): copy requirements, install with pip, install chromium via `playwright install chromium`
- [ ] Ensure `PLAYWRIGHT_BROWSERS_PATH` is set to a known path inside the image
- [ ] Add `.dockerignore` (exclude `.git`, `tests/`, `*.db`, `data/`, `.env`)
- [ ] Document required environment variables in a comment at the top of the Dockerfile
- [ ] Test: `docker build -t visa-checker .` completes in under 5 minutes on a standard machine

## Acceptance Criteria
- `docker run visa-checker visa-checker --help` prints the CLI help
- Image size is under 2GB
- Container runs as a non-root user
