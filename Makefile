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

.PHONY: test-unit
test-unit: install ## Run the unit test suite using pytest
	uv run pytest tests/unit/

.PHONY: test-integration
test-integration: install ## Run the integration test suite using pytest
	uv run pytest tests/integration/

.PHONY: test-acceptance
test-acceptance: test-integration ## Run the acceptance test suite (currently aliased to integration)

.PHONY: test
test: test-unit test-integration ## Run all test suites using pytest

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
run: up ## Run the full stack using docker compose (no image rebuild)

.PHONY: run-build
run-build: up-build ## Run the full stack and rebuild images

.PHONY: run-api
run-api: ## Start only the API service (and dependencies) without rebuilding
	$(COMPOSE) up -d $(APP)

.PHONY: run-api-build
run-api-build: ## Start only the API service (and dependencies) and rebuild API image
	$(COMPOSE) up -d --build $(APP)

.PHONY: dev
dev: migrate ## Run the local app with uvicorn and docker db
	uv run uvicorn books_rec_api.main:app --reload --host 0.0.0.0 --port 8000

# ==============================================================================
# Infrastructure & Docker Compose
# ==============================================================================

.PHONY: up
up: ## Start the full stack in the background
	$(COMPOSE) up -d --remove-orphans

.PHONY: up-build
up-build: ## Start the full stack in the background and rebuild images
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

.PHONY: verify-docker
verify-docker: ## Run Docker Compose smoke verification
	./verify_docker.sh

# ==============================================================================
# Database Operations
# ==============================================================================

.PHONY: db
db: ## Start only the database container
	$(COMPOSE) up -d --wait db

.PHONY: reset-db
reset-db: ## Stop containers and wipe the database volume
	$(COMPOSE) down -v

.PHONY: db-shell
db-shell: ## Open a psql shell to the database
	$(COMPOSE) exec db psql -U myuser -d books_rec

.PHONY: migrate
migrate: db ## Run database migrations
	uv run alembic upgrade head

.PHONY: check-users
check-users: ## Check the users table in the database
	$(COMPOSE) exec db psql -U myuser -d books_rec -c "\d users" -c "SELECT * FROM users;"

# ==============================================================================
# Evaluation
# ==============================================================================

.PHONY: ci-eval
ci-eval: ## Run CI evaluation for a scenario (e.g., make ci-eval SCENARIO=similar_books_smoke)
	uv run python scripts/ci_eval.py --scenario $(SCENARIO)

.PHONY: promote-baseline
promote-baseline: ## Promote a run to baseline (e.g., make promote-baseline SCENARIO=similar_books_smoke RUN_ID=run_123)
	uv run python -c "from eval.baseline import promote_baseline; promote_baseline('$(SCENARIO)', '$(RUN_ID)')"
	@echo "Promoted run $(RUN_ID) to baseline for scenario $(SCENARIO)"
