## Summary
Define the normalised `SlotResult` domain model returned by every scraper, so alert channels and state management work with a single consistent structure regardless of provider.

## Data Model

```python
@dataclass
class SlotResult:
    provider: str          # "vfs_global" | "tlscontact" | "bls" | "capago"
    country: str           # "France", "Germany", etc.
    centre: str            # "London", "Edinburgh", etc.
    visa_type: str         # "short_stay", "long_stay", etc.
    date: date             # the available appointment date
    time: time | None      # specific slot time if known
    booking_url: str       # direct deep-link to the booking page
    checked_at: datetime   # UTC timestamp of when this was found

    @property
    def slot_id(self) -> str:
        """Stable deduplication key."""
        return f"{self.provider}:{self.country}:{self.centre}:{self.date.isoformat()}"
```

## Tasks
- [ ] Implement `SlotResult` as a frozen `dataclass` or Pydantic model
- [ ] Add `slot_id` property for deduplication
- [ ] Add `is_within_range(earliest, latest)` helper method
- [ ] Write unit tests for `slot_id` stability and `is_within_range` edge cases

## Acceptance Criteria
- Two `SlotResult` objects for the same slot on the same day produce identical `slot_id` values
- `is_within_range` correctly handles boundary dates
- Model is importable from `visa_checker.models`
