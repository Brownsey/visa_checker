## Summary
Implement human-like interaction helpers that make the automation behave like a real user — variable typing speed, random mouse paths, natural scroll, and realistic inter-action pauses.

## Tasks
- [ ] Create `visa_checker/browser/human.py` module
- [ ] `human_type(page, selector, text)` — types character by character with random delays (50–200ms per character, occasional typo+backspace)
- [ ] `human_click(page, selector)` — moves mouse in a curved arc to the element before clicking, with a small random offset from centre
- [ ] `human_scroll(page, distance)` — scrolls in variable-speed increments
- [ ] `human_wait(min_ms, max_ms)` — async sleep with a uniform random duration
- [ ] `random_mouse_movement(page, n=3)` — make n random mouse moves to build up a realistic mouse trail before interacting
- [ ] All delays configurable via a `BehaviourConfig` dataclass (so tests can pass `min_delay=0`)

## Acceptance Criteria
- All helpers accept an optional `BehaviourConfig` that can set all delays to 0 for testing
- Typing a 20-character string takes between 1s and 4s with default config
- No interaction bypasses these helpers within scraper code
