# Evaluation Platform - Stage 1 Plan: Smoke Scenario + Raw Artifacts

## Objective
Produce a repeatable correctness signal with raw artifacts for Similar Books. Stage 1 implements the first complete decision loop with a deterministic load generator (`loadgen`), versioned scenario configurations, and correctness-only pass/fail gating.

## Stage 1 Contract (Normative)
- **Gate Scope:** Stage 1 gate is correctness-only. Latency and throughput are informational and must not affect pass/fail.
- **Scenario Stop Condition:** Exactly one of `duration_seconds` or `request_count` must be set in a scenario.
- **Anchor Selection:** Anchor sampling must be deterministic and seed-driven.
  - Same `seed` + same database snapshot -> identical anchor sequence.
  - Different `seed` on the same snapshot -> different anchor sequence (subject to dataset limits).
- **Deterministic Failure Semantics:** Any request that does not produce a valid passing response must be recorded as a correctness failure with a typed `failure_type`.
- **Artifact Compatibility:** Raw artifacts must include a `schema_version` field to allow evaluator/loadgen evolution without silent breakage.

## Actionable Steps

### 1. Create Scenario Configuration
- **Define Scenario Schema (`eval/schemas/scenario.py`):**
  - Traffic controls:
    - `concurrency` (bounded, >0).
    - Exactly one of `duration_seconds` or `request_count`.
  - Anchor inputs:
    - `anchor_count`.
    - Optional anchor filters.
  - Validation rules:
    - `status_code == 200`.
    - Response has key `similar_book_ids`.
    - `similar_book_ids` is an array of integer IDs.
    - No duplicates in `similar_book_ids`.
    - Anchor ID is not present in `similar_book_ids`.
- **Create Smoke Scenario (`scenarios/similar_books_smoke.yaml`):**
  - Small deterministic anchor set (e.g., 50-100 anchors).
  - Bounded concurrency.
  - One explicit stop condition (`request_count` recommended for smoke).

### 2. Build the Load Generator (`eval/loadgen.py`)
- **Initialization:**
  - Read `run.json` (from orchestrator) and target `scenarios/*.yaml`.
  - Validate scenario schema before execution.
- **Deterministic Anchor Selection:**
  - Select candidate anchor IDs deterministically from the DB.
  - Derive final anchor sequence from `seed` in `run.json`.
  - Do not use unseeded head-of-table selection as final sampling logic.
- **Traffic Execution:**
  - Use `asyncio` + `httpx` with bounded concurrency.
  - Stop based on the single configured stop condition.
- **Validation and Artifact Generation:**
  - Evaluate each response against scenario rules.
  - Write `raw/loadgen_results.json` with `schema_version` and run-level counts.
  - Write `raw/validation_failures.jsonl` with one record per failure, including at least:
    - `request_id`
    - `anchor_id`
    - `failure_type`
    - `status_code` (when available)
    - `error_detail` (when available)
  - Include non-HTTP failures (timeout, connection error, invalid JSON) as correctness failures.

### 3. Integrate Load Generator into Pipeline
- **Refactor Orchestrator (`scripts/eval_orchestrator.py`):**
  - Remove dummy test logic.
  - Keep responsibility limited to run initialization and `run.json` construction.
- **Update Runner (`scripts/eval_run.sh`):**
  - Execute pipeline in this order:
  - `uv run python scripts/eval_orchestrator.py`
  - `uv run python eval/loadgen.py`
  - `uv run python eval/evaluator.py`

### 4. Update Evaluator for Pass/Fail Criteria
- **Ingest Raw Artifacts:**
  - Read `raw/validation_failures.jsonl` and `raw/loadgen_results.json`.
  - Assert supported `schema_version`.
- **Summarize Results:**
  - Write `summary/summary.json` with correctness totals:
    - total requests attempted
    - total passed
    - total failed
    - failures by `failure_type`
- **Enforce Gate:**
  - Exit non-zero if `total_failed > 0`.
  - Ignore latency/throughput values for gate decision in Stage 1.

## Acceptance Criteria
- A smoke scenario cannot validate if both or neither of `duration_seconds`/`request_count` are provided.
- Re-running with identical `seed` and unchanged DB snapshot yields identical anchor IDs and identical pass/fail outcomes.
- Any timeout/connection/parsing/validation issue appears in `validation_failures.jsonl` with a typed `failure_type`.
- Evaluator gate fails whenever any correctness failure exists, and passes when none exist.
