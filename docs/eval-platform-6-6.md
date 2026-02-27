# Stage 6 Rollout Plan (Refined)

Based on the current implementation state of `docs/eval-platform-6.md` and the existing codebase, Phases A and B of the rollout are fully complete. Phases C and D have been mostly implemented but lack final verification and documentation updates. This document defines the exact steps remaining to formally complete Stage 6.

## Current State

*   **Phase A (Contract/Storage):** Completed. `telemetry_events` table exists with proper unique constraints.
*   **Phase B (Synthetic Emission):** Completed. `loadgen.py` emits `similar_impression` and `similar_click` deterministically based on synthetic config.
*   **Phase C (Evaluator Read/Export):** Implemented in code (`evaluator.py`, `metrics.py`, `telemetry.py`), but needs verification. `telemetry_extract.jsonl` is generated. CTR@K is computed.
*   **Phase D (Report/Summary):** Implemented in code. `RunSummary` schema has `quality_metrics`. `rendering.py` adds a Quality Metrics section to the markdown report.

## Remaining Steps (To Be Executed)

### 1. Verify Evaluator Telemetry Pipeline (Phase C/D verification)

*   [ ] **End-to-End Verification Run**: Execute a complete evaluation run (for example `make ci-eval SCENARIO=similar_books_smoke` or equivalent command with synthetic telemetry enabled) to ensure events are successfully written to the database and extracted.
*   [ ] **Artifact Inspection**: Verify `artifacts/eval/<run_id>/raw/telemetry_extract.jsonl` is created and correctly formatted. Expected top-level fields are `event_name`, `run_id`, `is_synthetic`, `ts`, and nested `payload` containing evaluator-join/dedupe fields (including `request_id` and `idempotency_key`).
*   [ ] **Extractor Contract Check**: Confirm extract schema is intentionally metrics-focused for offline reproducibility and does not require ingestion-only fields such as `telemetry_schema_version`.
*   [ ] **Summary Validation**: Verify `artifacts/eval/<run_id>/summary/summary.json` contains populated `quality_metrics` (including CTR@K and CTR by position).
*   [ ] **Report Validation**: Verify `artifacts/eval/<run_id>/report/report.md` contains the `Quality Metrics (Telemetry)` section, separating synthetic and real traffic (or showing the synthetic bucket clearly), and showing the Data Sufficiency Warning if impressions < 100.

### 2. Verify Offline Reproducibility

*   [ ] **Offline Recomputation Test**: Ensure that if the database is inaccessible, running the evaluator script on an existing `run_id` that already has `raw/telemetry_extract.jsonl` successfully parses the JSONL and yields the exact same CTR@K and position curve metrics.
*   [ ] **Unit Tests**: Add or ensure tests exist in `tests/unit/eval_platform/test_metrics.py` (and/or evaluator telemetry tests) asserting that `compute_quality_metrics` computes the exact same values from a fixed fixture simulating `telemetry_extract.jsonl` rows.

### 3. Documentation Updates and Cleanup

*   [ ] Update the checklist in `docs/eval-platform-6.md` section `11) Done Checklist` to mark the remaining items as complete:
    *   `[x] evaluator telemetry query by run_id implemented`
    *   `[x] raw/telemetry_extract.jsonl generated`
    *   `[x] summary/report quality section added`
*   [ ] Update `docs/eval-platform-staged.md` (if applicable) to mark Stage 6 as complete.

### 4. Phase E: Compatibility Cleanup (Future/Optional)

*   [ ] Review if any transitional `eval_run_id` to `run_id` compatibility mapping exists in `src/books_rec_api/services/telemetry_service.py` or the API payload schema. If present, plan its removal for a future release cycle.

## Acceptance Criteria

Stage 6 is strictly done when:
1. Evaluator computes CTR@K from telemetry queried by `run_id` only.
2. Recomputed CTR@K from `raw/telemetry_extract.jsonl` matches summary output.
3. Duplicate event submissions do not inflate CTR metrics.
4. Report and summary clearly separate synthetic vs real telemetry.
5. Stage 3/4 hard gates remain unchanged; quality metrics remain soft.
