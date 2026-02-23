.DEFAULT_GOAL := help

.PHONY: help
help:
	@echo "make sync | make install | make fmt | make lint | make type | make test | make openapi | make ci | make run | make docker-build | make docker-run | make docker-up | make docker-down"

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
run:
	uv run uvicorn books_rec_api.main:app --reload --host 0.0.0.0 --port 8000

.PHONY: docker-build
docker-build:
	docker build -t books-rec-api .

.PHONY: docker-run
docker-run:
	docker run -p 8000:8000 books-rec-api

.PHONY: docker-up
docker-up:
	docker compose up -d --build

.PHONY: docker-down
docker-down:
	docker compose down
