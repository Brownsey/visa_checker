## Summary
Define the abstract `BaseScraper` interface that every provider scraper must implement, ensuring a uniform contract for the orchestrator to call regardless of the underlying provider.

## Interface

```python
class BaseScraper(ABC):
    def __init__(self, config: TargetConfig, browser: BrowserEngine, ...): ...

    async def login(self) -> None:
        """Authenticate with the provider. May be a no-op if session is valid."""

    async def check_slots(self) -> list[SlotResult]:
        """Return all available slots matching the configured target."""

    async def is_logged_in(self) -> bool:
        """Check whether the current session is still authenticated."""

    @property
    def provider_name(self) -> str:
        """e.g. 'vfs_global'"""
```

## Tasks
- [ ] Implement `BaseScraper` abstract class in `visa_checker/scrapers/base.py`
- [ ] Add a `run_once() -> list[SlotResult]` concrete method that:
  1. Checks `is_logged_in()`; calls `login()` if not
  2. Calls `check_slots()`
  3. Catches `ScraperError` and logs before re-raising
- [ ] Create `ScraperRegistry` that maps provider name strings to scraper classes
- [ ] Write unit tests for `run_once` retry logic using a mock subclass

## Acceptance Criteria
- All provider scrapers pass `isinstance(scraper, BaseScraper)`
- `run_once()` handles `ScraperError` without crashing the scheduler
- `ScraperRegistry` raises `KeyError` for unknown provider names
