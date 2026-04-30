## Summary
Create a `docker-compose.yml` for one-command deployment with proper volume mounts, environment variable handling, and automatic restart.

## Tasks
- [ ] Write `docker-compose.yml`:
```yaml
services:
  visa-checker:
    build: .
    image: visa-checker:latest
    restart: unless-stopped
    env_file: .env
    volumes:
      - ./config/config.yaml:/app/config/config.yaml:ro
      - visa_checker_data:/app/data        # SQLite DB + session cookies
    command: visa-checker run

volumes:
  visa_checker_data:
```
- [ ] Write `docker-compose.override.yml` for local development (headed browser, verbose logging)
- [ ] Update `.env.example` with all variables needed for Docker deployment
- [ ] Add a `Makefile` with targets: `build`, `up`, `down`, `logs`, `check-now`, `test-alerts`
- [ ] Document deployment steps in `DEPLOY.md` (create VPS, copy files, set env vars, `make up`)

## Acceptance Criteria
- `docker compose up -d` starts the monitor in detached mode
- `docker compose logs -f` shows poll activity
- `docker compose exec visa-checker visa-checker status` returns circuit state
- Container auto-restarts on crash (tested by killing the process inside)
