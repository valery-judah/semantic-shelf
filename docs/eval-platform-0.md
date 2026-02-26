# Stage 0 Implementation Plan: Evaluation Contract and Run Identity

This document is an implementation checklist derived from [eval-platform.md](./eval-platform.md), which is the source of truth for stage sequencing and contracts.

This plan details the implementation of **Stage 0** for the incremental evaluation platform, ensuring all artifacts and API logs are tied to specific execution runs.

## 1. App Logging Middleware & Context Variables

**Goal:** Extract evaluation headers from incoming requests and inject them into structured application logs.

- **Changes in `src/books_rec_api/main.py`:**
  - Create a FastAPI middleware (or integrate via a global dependency if more appropriate) to inspect incoming HTTP requests.
  - Read `X-Eval-Run-Id` and `X-Request-Id` headers.
  - Use `contextvars` to set `run_id` and `eval_request_id` context variables for the lifetime of the request.

- **Changes in `src/books_rec_api/logging_config.py`:**
  - Define `contextvars` for the tracking variables.
  - Update `JsonFormatter` to conditionally include `run_id` and `request_id` in the JSON log payload if they are present in the current context.

- **Testing:**
  - Add unit tests validating that incoming requests with these headers correctly update the JSON log output.

## 2. Evaluation Schemas (`eval/schemas/`)

**Goal:** Establish strict data contracts for our runs and metrics via Pydantic models.

- **Create `eval/schemas/run.py`:**
  - Define a Pydantic model (`RunMetadata`) that captures fields such as:
    - `run_id`
    - timestamps
    - `scenario_id` and `scenario_version`
    - `git_sha` or other code versioning details
    - `dataset_id` / `seed` (for determinism)
    - `run_schema_version`

- **Create `eval/schemas/summary.py`:**
  - Define a Pydantic model (`RunSummary`) that captures fields such as:
    - counts (e.g., total requests, error rate, timeouts, correctness failures)
    - latency metrics (e.g., p50, p95, p99)
    - `summary_schema_version`

- **Testing:**
  - Write schema validation tests.

## 3. Minimal Orchestrator (`scripts/eval_orchestrator.py`)

**Goal:** Automate the creation of a run boundary and directories, proving the end-to-end identity propagation.

- **Implementation Details:**
  - Generates a universally unique `run_id` (UUID).
  - Creates the foundational artifact directory structure:
    - `artifacts/eval/<run_id>/raw/`
    - `artifacts/eval/<run_id>/summary/`
    - `artifacts/eval/<run_id>/report/`
  - Writes a valid `run.json` into the run's root directory, matching the Pydantic schema defined above.
  - Writes deterministic anchor selections to `raw/anchors.json` and request results to `raw/requests.jsonl`.
  - Generates a dummy/test API request against a local running instance, passing `X-Eval-Run-Id` and `X-Request-Id` to demonstrate that the logging infrastructure correctly tracks the run.

## 4. Stub Evaluator (`eval/evaluator.py`)

**Goal:** Validate inputs and establish the metric generation baseline.

- **Implementation Details:**
  - Accepts a `--run-id` CLI argument.
  - Reads `artifacts/eval/<run_id>/run.json` and parses it via the Pydantic schema.
  - Generates a dummy `summary.json` file, populating it with empty/stub metrics, and writes it to `artifacts/eval/<run_id>/summary/summary.json` validating against the Pydantic schema.

## Next Steps

Once this plan is approved, we should switch into **Code Mode** to implement these tasks sequentially.
