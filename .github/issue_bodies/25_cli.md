## Summary
Build a Click-based CLI so the tool can be started, tested, and queried from the terminal.

## Commands

```
visa-checker run [--config PATH]
    Start the continuous monitoring loop.

visa-checker check-now [--config PATH] [--provider vfs_global|tlscontact|bls|capago]
    Run a single check across all (or one) configured target(s) and print results.
    Does not write to state or send alerts.

visa-checker test-alerts [--config PATH]
    Send a test notification to all configured alert channels.

visa-checker history [--days 7]
    Show the slot availability history from the local database.
    Displays as a table: date, provider, country, centre, first_seen, alerted.

visa-checker status
    Show circuit breaker state, last poll times, and consecutive failure counts.
```

## Tasks
- [ ] Create Click group `cli` in `visa_checker/cli/main.py`
- [ ] Register as `visa-checker` entry point in `pyproject.toml`
- [ ] `run` command: initialise config, state, browser engine, alert dispatcher, orchestrator; block until SIGINT
- [ ] `check-now` command: one-shot scraper run, print `SlotResult` table to stdout
- [ ] `test-alerts` command: call `dispatcher.test_all()`, print success/failure per channel
- [ ] `history` command: query `StateManager.get_history(days)`, render with `rich` table
- [ ] `status` command: print circuit breaker and last poll state from the database
- [ ] Use `rich` for all terminal output (tables, coloured status)

## Acceptance Criteria
- `visa-checker --help` documents all subcommands
- `visa-checker check-now` runs without starting the scheduler
- `visa-checker run` starts monitoring and exits cleanly on Ctrl+C
