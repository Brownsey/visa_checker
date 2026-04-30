.PHONY: build up down logs check-now test-alerts test lint

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

check-now:
	docker compose exec visa-checker visa-checker check-now

test-alerts:
	docker compose exec visa-checker visa-checker test-alerts

test:
	uv run pytest

lint:
	uv run ruff check .
	uv run ruff format --check .
