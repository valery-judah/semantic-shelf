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
- **`make run`** - Runs both the application and database within Docker Compose (starts the full stack without rebuilding images).
- **`make run-build`** - Same as `make run`, but forces a rebuild of images.

## Local Testing & Authentication
The API relies on an external Identity Provider and expects an `X-User-Id` header to identify users. The application automatically provisions a "shadow user" profile in the database the first time it encounters a new `X-User-Id`.

### Testing via Swagger UI
This setup makes it very easy to test user-specific scenarios (like recommendations or preference updates) directly from the documentation UI:
1. Run the app (`make dev` or `make run`).
2. Navigate to [http://localhost:8000/docs](http://localhost:8000/docs).
3. Click the **Authorize** button at the top right.
4. Enter any test user ID (e.g., `user-scifi-fan`, `test-user-123`) in the `X-User-Id` field.
5. Swagger will automatically attach this header to all subsequent requests.

### Simulating Different Users
Because of the automatic provisioning, you can easily simulate distinct user scenarios for recommendations simply by changing the ID:
- Provide `X-User-Id: user-scifi-fan`, update their preferences to prefer Sci-Fi, and check their recommendations.
- Provide `X-User-Id: user-fantasy-fan`, update their preferences to prefer Fantasy, and check their recommendations.
- Switch back to `user-scifi-fan` anytime, and the system will reload the exact profile and preferences you saved for them earlier.

## Commands
### Development & Lifecycle
- `make sync` - install dependencies with uv
- `make dev` - start local db and run FastAPI app locally with fast reload
- `make run` - run full stack (app + db) via Docker Compose without rebuilding
- `make run-build` - run full stack and rebuild Docker images
- `make run-api` - run only API service (and dependencies) without rebuilding
- `make run-api-build` - run only API service (and dependencies) and rebuild API image
- `make down` - stop and remove Docker Compose containers
- `make logs` - tail the logs of the Docker Compose stack
- `make reset-db` - clear the database volumes

## Dataset Import
- The Goodbooks source repository is `GOODBOOKS_SOURCE_REPO=https://github.com/malcolmosh/goodbooks-10k-extended.git`.
- Before first run, clone it locally (for example next to this repo):
  - `git clone "$GOODBOOKS_SOURCE_REPO" ../goodbooks-10k-extended`
- In your `.env`, set these variables:
  - `GOODBOOKS_SOURCE_REPO="https://github.com/malcolmosh/goodbooks-10k-extended.git"`
  - `GOODBOOKS_DATASET_DIR="../goodbooks-10k-extended"`
- Import documentation: [`scripts/import.md`](scripts/import.md)
- Rationale (short): we keep imported Goodbooks data in the existing app schema so the current `books` API stays the canonical read path, while normalized interaction tables (`dataset_users`, `ratings`, `to_read`, `tags`, `book_tags`) enforce referential integrity and support recommendation workflows.
- First-boot auto-seed: on a fresh DB volume, Postgres runs `docker-entrypoint-initdb.d` scripts and seeds `books` from `${GOODBOOKS_DATASET_DIR}/books_enriched.csv`.
- If you already initialized the DB volume and want to re-run first-boot seed scripts: `make reset-db` then start again with `make run` or `make dev`.

### Quality Gates
- `make test` - run tests
- `make fmt` - format and auto-fix lint
- `make lint` - lint check
- `make type` - run mypy
