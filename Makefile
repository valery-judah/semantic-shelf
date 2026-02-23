.DEFAULT_GOAL := help
COMPOSE = docker compose
APP = api

.PHONY: help
help: ## Show this help message
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST) | sort

# ==============================================================================
# Environment & Dependencies
# ==============================================================================

.PHONY: sync
sync: ## Sync dependencies using uv
	uv sync

.PHONY: install
install: sync ## Install the package in editable mode for local development
	uv pip install --editable .

# ==============================================================================
# Development & Quality Assurance
# ==============================================================================

.PHONY: fmt
fmt: ## Format the code using ruff
	uv run ruff format .
	uv run ruff check . --fix

.PHONY: lint
lint: ## Lint the code using ruff
	uv run ruff format . --check
	uv run ruff check .

.PHONY: type
type: ## Run type checking using mypy
	uv run mypy src

.PHONY: test
test: install ## Run the test suite using pytest
	uv run pytest

.PHONY: openapi
openapi: install ## Generate the OpenAPI schema
	uv run python scripts/generate_openapi.py

.PHONY: ci
ci: ## Run the full CI pipeline script locally
	./scripts/ci_pipeline.sh

# ==============================================================================
# Execution
# ==============================================================================

.PHONY: run
run: up ## Run the full stack using docker compose

.PHONY: dev
dev: db ## Run the local app with uvicorn and docker db
	uv run uvicorn books_rec_api.main:app --reload --host 0.0.0.0 --port 8000

# ==============================================================================
# Infrastructure & Docker Compose
# ==============================================================================

.PHONY: up
up: ## Start the full stack in the background
	$(COMPOSE) up -d --build --remove-orphans

.PHONY: down
down: ## Stop and remove the full stack containers
	$(COMPOSE) down

.PHONY: ps
ps: ## List running containers
	$(COMPOSE) ps

.PHONY: logs
logs: ## Tail the logs of all containers
	$(COMPOSE) logs -f --tail=200

.PHONY: build
build: ## Build the docker images
	$(COMPOSE) build

.PHONY: restart
restart: ## Restart the docker containers
	$(COMPOSE) restart

# ==============================================================================
# Database Operations
# ==============================================================================

.PHONY: db
db: ## Start only the database container
	$(COMPOSE) up -d db

.PHONY: reset-db
reset-db: ## Stop containers and wipe the database volume
	$(COMPOSE) down -v

.PHONY: db-shell
db-shell: ## Open a psql shell to the database
	$(COMPOSE) exec db psql -U myuser -d books_rec

.PHONY: check-users
check-users: ## Check the users table in the database
	$(COMPOSE) exec db psql -U myuser -d books_rec -c "\d users" -c "SELECT * FROM users;"
