# Stage 6 Rollout Plan: Phase C (Evaluator Read + Export)

## Objective
Ensure the evaluator can successfully read telemetry events from the database, compute quality metrics (CTR@K, position curves), and export the raw data for offline reproducibility.

## Prerequisites
- Phase A (Contract/Storage) is complete.
- Phase B (Synthetic Emission) is complete.

## Implementation & Verification Steps

### 1. Verification of Evaluator DB Query
- [ ] Confirm `export_telemetry_extract` in `eval/telemetry.py` correctly queries the `telemetry_events` table filtered by `run_id`.
- [ ] Ensure the query retrieves all fields required for evaluator metric computation and offline replay (`event_name`, `run_id`, `is_synthetic`, `ts`, and payload fields such as `request_id`, `idempotency_key`, positions/books).

### 2. Verification of Telemetry Extract Generation
- [ ] Run a local evaluation using a scenario with synthetic telemetry enabled (e.g., `similar_books_quality` or `similar_books_smoke` with telemetry config).
- [ ] Inspect the generated `artifacts/eval/<run_id>/raw/telemetry_extract.jsonl` file.
- [ ] Validate the JSONL schema matches expectations (contains `event_name`, `run_id`, `is_synthetic`, `ts`, and nested `payload` with evaluator-join and dedupe fields).
- [ ] Confirm extractor schema remains intentionally metrics-focused for reproducibility. It should not require ingestion-only fields (for example `telemetry_schema_version`) because evaluator parsing and `compute_quality_metrics` do not depend on them.

### 3. Verification of Quality Metrics Computation
- [ ] Review `eval/metrics.py::compute_quality_metrics` to ensure CTR@K calculation handles denominators (impressions with position < K) and numerators (matched clicks with position < K) correctly.
- [ ] Confirm deduplication logic based on `idempotency_key` functions as expected.

### 4. Testing Offline Reproducibility (Crucial for Phase C)
- [ ] Write a test in `tests/unit/eval_platform/test_metrics.py` (or similar) that:
  1. Loads a fixture `telemetry_extract.jsonl`.
  2. Runs `read_telemetry_extract` and `compute_quality_metrics`.
  3. Asserts the computed metrics match known expected values.
- [ ] Manually simulate an offline run:
  1. Take an existing `artifacts/eval/<run_id>` directory.
  2. Stop the Postgres database (`docker compose stop db`).
  3. Re-run `uv run python eval/evaluator.py --run-id <run_id>`.
  4. Verify the script reads from the existing `telemetry_extract.jsonl` and successfully produces the same `summary.json`.

## Acceptance Criteria
- Evaluator computes CTR@K from telemetry queried by `run_id`.
- Recomputed CTR@K from `raw/telemetry_extract.jsonl` exactly matches the original summary output.
- Duplicate event submissions do not inflate CTR metrics.
