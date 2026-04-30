## Summary
Set up the base Python project structure so all other epics have a consistent foundation to build on.

## Tasks
- [ ] Initialise Poetry project with `pyproject.toml`
- [ ] Create directory structure:
```
visa_checker/
  scrapers/        # provider scrapers
  browser/         # playwright engine
  anti_detection/  # proxy, captcha, fingerprinting
  alerts/          # notification channels
  scheduler/       # polling orchestrator
  state/           # SQLite state manager
  cli/             # Click CLI
  models/          # shared domain models
tests/
  scrapers/
  alerts/
  integration/
config/
  config.example.yaml
```
- [ ] Add core dependencies: `playwright`, `pydantic>=2`, `apscheduler`, `click`, `loguru`, `aiosqlite`, `httpx`, `pyyaml`
- [ ] Add dev dependencies: `pytest`, `pytest-asyncio`, `ruff`, `mypy`
- [ ] Configure `ruff` for linting and formatting (`pyproject.toml`)
- [ ] Add `.gitignore` (Python, .env, cookies/, *.db, .playwright/)
- [ ] Add `.env.example` listing every required environment variable key

## Acceptance Criteria
- `poetry install` completes without errors
- `ruff check .` passes on the empty scaffolding
- `pytest` discovers and passes a smoke test
- Project directory structure matches the layout above
