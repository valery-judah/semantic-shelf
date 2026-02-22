.DEFAULT_GOAL := help

.PHONY: help
help:
	@echo "make sync | make install | make fmt | make lint | make type | make test | make run"

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

.PHONY: run
run:
	uv run uvicorn books_rec_api.main:app --reload --host 0.0.0.0 --port 8000
