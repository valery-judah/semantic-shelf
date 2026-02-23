# Books Recommendation API (MVP)

## Requirements
- Python 3.11+
- uv
- Docker (with Docker Compose)

## Setup
1. Copy the example environment file: `cp .env.example .env`
2. Install dependencies: `make sync`

## Running the Application
We support two primary patterns for running the app depending on your workflow:

### Pattern A: Fast Inner-Loop (Recommended for daily dev)
- **`make dev`** - Starts only the database via Docker Compose and runs the FastAPI app natively on the host using `uvicorn --reload`. This gives fast hot-reloads and consistent DB behavior.

### Pattern B: Full Stack (Recommended for testing "production-like")
- **`make run`** - Runs both the application and database within Docker Compose (starts the full stack).

## Commands
### Development & Lifecycle
- `make sync` - install dependencies with uv
- `make dev` - start local db and run FastAPI app locally with fast reload
- `make run` - run full stack (app + db) via Docker Compose
- `make down` - stop and remove Docker Compose containers
- `make logs` - tail the logs of the Docker Compose stack
- `make reset-db` - clear the database volumes

### Quality Gates
- `make test` - run tests
- `make fmt` - format and auto-fix lint
- `make lint` - lint check
- `make type` - run mypy
