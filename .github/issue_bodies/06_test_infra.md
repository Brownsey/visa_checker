## Summary
Establish the test infrastructure: fixtures, mocks, and helpers that all other test suites depend on.

## Tasks
- [ ] Configure `pytest` with `pytest-asyncio` in `pyproject.toml` (asyncio_mode = "auto")
- [ ] Create `tests/conftest.py` with shared fixtures:
  - `config_fixture` — loads a minimal test config
  - `state_fixture` — in-memory `StateManager`
  - `mock_browser` — a mock Playwright page that can replay captured HTTP responses
  - `slot_factory` — factory function returning `SlotResult` instances with sane defaults
- [ ] Add `tests/fixtures/` directory with saved HTML snapshots from each provider (for offline scraper tests)
- [ ] Write a helper `record_provider_response(url)` script that saves a sanitised HTML snapshot for later replay (run manually, not in CI)
- [ ] Add `pytest-cov` and set minimum coverage gate at 70%

## Acceptance Criteria
- `pytest` runs green on a fresh clone with no network access (scrapers skip via mock)
- Coverage report is generated automatically
- `conftest.py` fixtures are documented with docstrings
