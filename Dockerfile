# ── Stage 1: build dependencies ──────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml ./
RUN uv pip install --system --no-cache -e ".[dev]" 2>/dev/null || \
    uv pip install --system --no-cache -r <(uv pip compile pyproject.toml --no-deps 2>/dev/null || echo "")

# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

# Required env vars (set via --env-file or docker compose env_file):
# VISA_CHECKER_CONFIG, VFS_EMAIL, VFS_PASSWORD, TLS_EMAIL, TLS_PASSWORD,
# TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, NTFY_TOPIC

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml ./
COPY visa_checker/ ./visa_checker/

# Install dependencies (no dev extras)
RUN uv pip install --system --no-cache .

# Install only Chromium (smaller image)
RUN playwright install chromium --with-deps

# Create non-root user
RUN useradd -m -u 1000 checker
RUN mkdir -p /app/data /app/config && chown -R checker:checker /app
USER checker

ENV VISA_CHECKER_CONFIG=/app/config/config.yaml
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

VOLUME ["/app/data", "/app/config"]

ENTRYPOINT ["visa-checker"]
CMD ["run"]
