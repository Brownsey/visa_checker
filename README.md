# Visa Checker

A continuous Schengen visa appointment slot monitor for UK residents. Polls VFS Global, TLScontact, BLS International, and Capago around the clock and fires instant alerts (Telegram, ntfy, email, SMS) the moment a slot opens.

## Architecture

The project follows **hexagonal architecture** (Ports and Adapters), keeping all domain logic completely isolated from I/O concerns.

```
visa_checker/
├── domain/              ← Pure business logic, no I/O
│   ├── models.py        ← SlotResult, SlotTarget
│   ├── errors.py        ← Exception hierarchy
│   └── logging.py       ← Logging configuration
│
├── ports/               ← Abstract interfaces (the "hexagon boundary")
│   ├── scraper.py       ← IScraper
│   ├── alert.py         ← IAlertChannel
│   ├── state.py         ← IStateRepository
│   ├── browser.py       ← IBrowserEngine
│   ├── proxy.py         ← IProxyProvider
│   └── captcha.py       ← ICaptchaSolver
│
├── adapters/            ← Concrete implementations of ports
│   ├── scrapers/        ← vfs_global, tls_contact, bls_international, capago
│   ├── alerts/          ← telegram, ntfy, email_channel, sms
│   ├── browser/         ← engine (Playwright+stealth), human helpers, sessions
│   ├── anti_detection/  ← proxy (file-based), captcha (2captcha), fingerprint
│   └── state/           ← sqlite_repository
│
├── application/         ← Application services (orchestration)
│   ├── orchestrator.py  ← APScheduler polling loop
│   ├── alert_dispatcher.py ← Fan-out to all alert channels
│   ├── circuit_breaker.py  ← Per-provider exponential backoff
│   └── factory.py       ← Composition root: wires everything together
│
├── cli/                 ← Primary driving adapter
│   └── main.py          ← Click CLI (run, check-now, test-alerts, history, status)
│
└── config/
    └── settings.py      ← Pydantic v2 settings + ${ENV_VAR} interpolation
```

### How a poll works

```
APScheduler (every ~90s ± 20% jitter)
    │
    ▼
CircuitBreaker.call(scraper.run_once())
    │
    ├─ scraper.is_logged_in() → login() if needed
    ├─ scraper.check_slots() → list[SlotResult]
    │
    ▼
Filter: slot.is_within_range(earliest_date, latest_date)
    │
    ▼
StateRepository.is_new(slot) → skip if already seen
    │
    ▼
StateRepository.mark_seen(slot)
    │
    ▼
AlertDispatcher.dispatch(slot)
    ├─ TelegramChannel.send(slot)
    ├─ NtfyChannel.send(slot)
    └─ EmailChannel.send(slot)  (if enabled)
```

---

## Quick start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (`pip install uv` or `winget install astral-sh.uv`)
- A Telegram bot token + chat ID (free, ~2 minutes to set up)

### 1 — Install dependencies

```bash
uv sync
playwright install chromium
```

### 2 — Configure

Copy the example config and fill in your details:

```bash
cp config/config.example.yaml config/config.yaml
```

Edit `config/config.yaml` and set at minimum:
- The `targets` section (which countries and date range you want)
- Credentials for each provider you're monitoring
- At least one alert channel (Telegram is recommended)

All `${VAR}` placeholders are read from environment variables. Create a `.env` file from the template:

```bash
cp .env.example .env
# Edit .env and fill in your values
```

> **Tip:** For Gmail, create an [App Password](https://myaccount.google.com/apppasswords) rather than using your main password.

### 3 — Run

```bash
# Start the continuous monitor
uv run visa-checker run

# One-shot check (no alerts, no state changes)
uv run visa-checker check-now

# Test all configured alert channels
uv run visa-checker test-alerts

# Show slot history
uv run visa-checker history --days 7

# Show circuit breaker state
uv run visa-checker status
```

---

## Proxies

All traffic is routed through `proxies.txt` by default. This prevents IP bans from repeated requests to the visa booking sites.

**Format** (one proxy per line, any of these styles):
```
# Plain host:port
185.199.228.220:7300

# With authentication
185.199.228.220:7300:username:password

# URL style
http://username:password@185.199.228.220:7300
```

**Behaviour:**
- Proxy is selected **randomly** on each browser session
- If a proxy fails to connect, it is **automatically removed** from the pool and the next one is tried
- Once all proxies are exhausted, the pool resets to the full list
- Set `proxies.enabled: false` in `config.yaml` to run without proxies

> **Note:** `proxies.txt` is in `.gitignore` — never commit it.

### Validating proxies at startup

Add an optional health-check before starting:

```python
# In your own script:
from visa_checker.adapters.anti_detection.proxy import FileProxyProvider
import asyncio

provider = FileProxyProvider("proxies.txt")
asyncio.run(provider.validate_all())
```

---

## Alert channels

| Channel | Cost | Setup |
|---------|------|-------|
| **Telegram** | Free | Create bot via @BotFather, get `bot_token` + `chat_id` |
| **ntfy.sh** | Free | Install [ntfy app](https://ntfy.sh), pick a unique topic |
| **Email** | Free (Gmail) | Enable 2FA, create an [App Password](https://myaccount.google.com/apppasswords) |
| **SMS** | ~£0.05/msg | Sign up at [twilio.com](https://www.twilio.com), get SID + token |

Test all channels at any time:

```bash
uv run visa-checker test-alerts
```

---

## CAPTCHA solving

VFS Global uses reCAPTCHA v2 on login; TLScontact uses hCaptcha. Without a solver, the scraper will raise `CaptchaError` when a CAPTCHA is encountered.

To enable automated solving:

1. Sign up at [2captcha.com](https://2captcha.com) (~$2 per 1000 solves)
2. Add your API key: `CAPTCHA_API_KEY=your_key` in `.env`
3. Set `captcha.provider: 2captcha` in `config.yaml`

---

## Provider coverage

| Provider | Countries |
|----------|-----------|
| **VFS Global** | Germany, Italy, Netherlands, Belgium, Denmark, Czech Republic, Ireland, Hungary, Latvia, Austria, Finland, Sweden, Norway, Poland |
| **TLScontact** | France, Portugal, Belgium, Denmark, Netherlands, Luxembourg |
| **BLS International** | Spain |
| **Capago** | Finland, Iceland |

---

## Deployment (24/7 on a VPS)

The recommended deployment is a cheap Linux VPS (e.g. Hetzner CX11, ~€3.50/month):

```bash
# On the VPS:
git clone https://github.com/Brownsey/visa_checker
cd visa_checker
cp config/config.example.yaml config/config.yaml
cp .env.example .env
nano .env          # fill in credentials
nano proxies.txt   # add your proxies

docker compose up -d
docker compose logs -f
```

**Useful commands:**
```bash
make logs          # tail logs
make check-now     # one-shot check
make test-alerts   # test all alert channels
```

### GitHub Actions (free alternative)

If you don't have a VPS, you can run the checker on GitHub's free compute. The scheduled workflow runs every 10 minutes.

Required GitHub Secrets (Settings → Secrets → Actions):

```
VISA_CHECKER_CONFIG_B64   base64-encoded contents of config.yaml
VFS_EMAIL / VFS_PASSWORD
TLS_EMAIL / TLS_PASSWORD
TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID
NTFY_TOPIC
CAPTCHA_API_KEY           (optional)
```

Encode your config:
```bash
base64 -w0 config/config.yaml
```

> **Note:** GitHub Actions has a minimum cron interval of 5 minutes and may delay up to 10 minutes under load. A VPS gives you true ~90-second polling.

---

## Development

```bash
uv sync --all-extras   # install with dev dependencies
uv run pytest          # run tests
uv run ruff check .    # lint
uv run ruff format .   # format
```

### Adding a new provider

1. Create `visa_checker/adapters/scrapers/my_provider.py`
2. Subclass `BaseScraper` and implement `provider_name`, `is_logged_in`, `login`, `check_slots`
3. Decorate with `@register_scraper("my_provider")`
4. Import in `factory.py` so the registry picks it up
5. Add `my_provider` to `ProviderName` in `domain/models.py` and `config/settings.py`

---

## How slots are detected

Each provider uses a different mechanism:

- **VFS Global** — logs in, navigates to the booking calendar, parses `[data-date]` elements not marked as disabled
- **TLScontact** — intercepts the AJAX calendar response (`page.on("response", ...)`) for efficient slot parsing, with DOM fallback
- **BLS International** — navigates to the appointment page for the selected centre, parses available date elements
- **Capago** — navigates to the country-specific appointment page, parses available date slots

Slot dates are normalised into `SlotResult` objects with a stable `slot_id` for deduplication. The SQLite state store ensures you only get alerted once per slot per day.
