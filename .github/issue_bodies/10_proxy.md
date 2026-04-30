## Summary
Add pluggable proxy rotation so the scraper can cycle through residential IP addresses, preventing IP bans from repeated requests.

## Background
VFS Global and TLScontact rate-limit by IP. After ~20 rapid requests, an IP may be blocked for 30–60 minutes. Residential proxies from services like BrightData make each request appear to originate from a different UK household.

## Tasks
- [ ] Create `ProxyProvider` abstract base class in `visa_checker/anti_detection/proxy.py`
- [ ] Implement `BrightDataProxyProvider` — generates per-request proxy URLs using the BrightData sticky-session endpoint
- [ ] Implement `FileProxyProvider` — reads a `proxies.txt` file (one `host:port:user:pass` per line) and round-robins
- [ ] Implement `NullProxyProvider` — no-op, used when proxies are disabled
- [ ] `ProxyProvider.next() -> ProxyConfig | None` — returns the next proxy to use
- [ ] Proxy config is injected into `BrowserEngine.new_page(proxy=...)` via Playwright's native proxy support
- [ ] Log which proxy IP was used per poll (useful for debugging bans)
- [ ] Add proxy health check: skip a proxy if it fails to load `https://httpbin.org/ip` within 5s

## Acceptance Criteria
- With a valid `proxies.txt`, each poll uses a different proxy IP
- A failed proxy is skipped and the next one is tried
- Proxies disabled (`proxies.enabled: false`) has zero performance overhead
