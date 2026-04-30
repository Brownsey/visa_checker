## Summary
Persist browser sessions (cookies + local storage) per provider so the system doesn't need to log in from scratch on every poll, reducing detection risk and login overhead.

## Tasks
- [ ] Create `SessionStore` in `visa_checker/browser/session.py`
- [ ] Store cookies as JSON files under `data/sessions/{provider}.json`
- [ ] `SessionStore.load(context, provider)` — injects saved cookies into a `BrowserContext`
- [ ] `SessionStore.save(context, provider)` — persists current cookies after a successful login
- [ ] `SessionStore.invalidate(provider)` — deletes stale session file (called on auth error)
- [ ] Sessions expire after a configurable TTL (default: 4 hours); expired sessions are auto-invalidated
- [ ] Each scraper should attempt to restore a session before triggering a full login flow
- [ ] Session files are excluded from git via `.gitignore`

## Acceptance Criteria
- VFS Global login is only performed once per 4-hour window (verified via poll log)
- Stale/expired sessions trigger re-login and a new session save
- Session files never contain plaintext passwords — only cookies
