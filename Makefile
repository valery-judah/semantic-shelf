.DEFAULT_GOAL := help
COMPOSE = docker compose
APP = api

.PHONY: help
help:
	@echo "make sync | make install | make fmt | make lint | make type | make test | make openapi | make ci"
	@echo "make run (full stack) | make dev (local app + docker db) | make db | make up | make down | make logs | make ps | make build | make restart | make reset-db"

.PHONY: sync
sync:
	uv sync

.PHONY: install
install: sync
	uv pip install --editable .

.PHONY: fmt
fmt:
	uv run ruff format .
	uv run ruff check . --fix

.PHONY: lint
lint:
	uv run ruff format . --check
	uv run ruff check .

.PHONY: type
type:
	uv run mypy src

.PHONY: test
test: install
	uv run pytest

.PHONY: openapi
openapi: install
	uv run python scripts/generate_openapi.py

.PHONY: ci
ci:
	./scripts/ci_pipeline.sh

.PHONY: run
run: up

.PHONY: dev
dev: db
	uv run uvicorn books_rec_api.main:app --reload --host 0.0.0.0 --port 8000

.PHONY: up
up:
	$(COMPOSE) up -d --build --remove-orphans

.PHONY: down
down:
	$(COMPOSE) down

.PHONY: ps
ps:
	$(COMPOSE) ps

.PHONY: logs
logs:
	$(COMPOSE) logs -f --tail=200

.PHONY: build
build:
	$(COMPOSE) build

.PHONY: restart
restart:
	$(COMPOSE) restart

.PHONY: db
db:
	$(COMPOSE) up -d db

.PHONY: reset-db
reset-db:
	$(COMPOSE) down -v
