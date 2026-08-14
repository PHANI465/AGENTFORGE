.PHONY: dev dev-prod down test test-unit test-integration lint seed migrate health logs clean

COMPOSE := docker compose -f infra/docker/docker-compose.yml -f infra/docker/docker-compose.override.yml --env-file .env
COMPOSE_PROD := docker compose -f infra/docker/docker-compose.yml --env-file .env

## ── Development ──────────────────────────────────────────────

dev:            ## Start all services with hot reload (edits restart uvicorn automatically)
	$(COMPOSE) up -d --build

dev-prod:       ## Start all services in production mode (no hot reload, baked images)
	$(COMPOSE_PROD) up -d --build

down:           ## Stop and remove all containers
	$(COMPOSE) down

logs:           ## Tail logs from all services
	$(COMPOSE) logs -f

health:         ## Check API Gateway health
	@curl -s http://localhost:8000/health | python -m json.tool

## ── Database ─────────────────────────────────────────────────

migrate:        ## Run Alembic migrations
	uv run --package agentforge-common alembic -c packages/common/alembic.ini upgrade head

seed:           ## Seed the database with sample data
	uv run --package agentforge-common python scripts/seed.py

## ── Testing ──────────────────────────────────────────────────

test:           ## Run all tests (unit + integration)
	uv run pytest tests/ -v

test-unit:      ## Run unit tests only
	uv run pytest tests/unit/ -v

test-integration: ## Run integration tests only (requires Postgres)
	uv run pytest tests/integration/ -v

## ── Code Quality ─────────────────────────────────────────────

lint:           ## Run ruff linter + formatter check
	uv run ruff check .
	uv run ruff format --check .

format:         ## Auto-format code with ruff
	uv run ruff format .
	uv run ruff check --fix .

## ── Cleanup ──────────────────────────────────────────────────

clean:          ## Remove Docker volumes and __pycache__
	$(COMPOSE) down -v
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true

## ── Help ─────────────────────────────────────────────────────

help:           ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
