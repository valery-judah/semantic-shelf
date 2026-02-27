# Stage 6 Acceptance Criteria Verification Strategy

This document outlines the detailed verification strategy to definitively prove the 5 acceptance criteria for Stage 6 defined in `docs/eval-platform-6.md`. It references existing test coverage and defines explicit steps or tests required to fully validate each condition.

## Evidence Map

| Criterion | Primary Evidence | What It Proves | Remaining Gap |
|---|---|---|---|
| 1. Evaluator computes CTR@K from telemetry queried by `run_id` only | `eval/telemetry.py::export_telemetry_extract`, `tests/unit/eval_platform/test_telemetry.py::test_export_telemetry_extract`, `tests/integration/test_telemetry_api.py::test_ingest_telemetry_events_rejects_eval_run_id_only_payload` | Query path uses `run_id` filter and API contract enforces strict `run_id` payloads | Need live-DB integration test with mixed `run_id` data and export assertion |
| 2. Recomputed CTR@K from `raw/telemetry_extract.jsonl` matches summary output | `tests/unit/eval_platform/test_stage6_acceptance.py::test_stage6_acceptance_quality_metrics_integration`, `tests/unit/eval_platform/test_metrics.py::test_offline_reproducibility` | Extract parsing and metric recomputation match summary quality metrics | None |
| 3. Duplicate event submissions do not inflate CTR metrics | `tests/integration/test_telemetry_api.py::test_ingest_telemetry_events_duplicate_idempotency`, `tests/unit/eval_platform/test_metrics.py::test_deduplication` | DB-level dedupe and in-memory dedupe both prevent metric inflation | None |
| 4. Report and summary clearly separate synthetic vs real telemetry | `tests/unit/eval_platform/test_metrics.py::test_traffic_splitting`, `tests/unit/eval_platform/test_stage6_acceptance.py::test_stage6_acceptance_quality_metrics_integration` | Canonical buckets and report sections for synthetic/real/combined are present | None |
| 5. Stage 3/4 hard gates remain unchanged; quality metrics remain soft | `eval/evaluator.py` gate logic, `tests/unit/eval_platform/test_stage6_acceptance.py::test_stage6_acceptance_quality_metrics_integration` | Stage 6 path keeps quality metrics as non-gating signal (quality section does not force fail) | Current evidence here is scoped to non-gating behavior in Stage 6 path |

## 1. Evaluator computes CTR@K from telemetry queried by `run_id` only.
**Objective**: Ensure that the evaluator queries the telemetry database strictly by `run_id` without pulling in events from other runs or relying on aliases.

**Current Coverage**:
- `tests/integration/test_telemetry_api.py::test_ingest_telemetry_events_rejects_eval_run_id_only_payload` verifies that the API explicitly rejects the old `eval_run_id` alias, enforcing strict `run_id` payloads.
- `eval/telemetry.py::export_telemetry_extract` correctly queries `select(DbTelemetryEvent).where(DbTelemetryEvent.run_id == run_id)`.
- `tests/unit/eval_platform/test_telemetry.py::test_export_telemetry_extract` mocks the DB and asserts the export format, but doesn't do a full integration test with multiple `run_id`s in a real DB.

**Actionable Verification Steps**:
1. **Write a new integration test** in `tests/integration/test_telemetry_api.py` (or a new file `tests/integration/test_eval_telemetry_export.py`):
   - Insert telemetry events for two different `run_id`s (e.g., `run_A` and `run_B`) into the database via the API or direct DB session.
   - Call `eval.telemetry.export_telemetry_extract("run_A", tmp_path)`.
   - Assert that the resulting `telemetry_extract.jsonl` is non-empty and that every exported row has `run_id == "run_A"`.
   - Assert that no exported row includes identifiers unique to `run_B` fixtures.

## 2. Recomputed CTR@K from `raw/telemetry_extract.jsonl` matches summary output.
**Objective**: Verify that `telemetry_extract.jsonl` contains the exact same data used to populate `summary.json`, ensuring full offline reproducibility.

**Current Coverage**:
- `tests/unit/eval_platform/test_stage6_acceptance.py::test_stage6_acceptance_quality_metrics_integration` creates a mock `telemetry_extract.jsonl`, runs the evaluator, and successfully verifies that `summary.json` contains matching, accurate metrics.
- `tests/unit/eval_platform/test_metrics.py::test_offline_reproducibility` verifies that `read_telemetry_extract` parses the JSONL and yields identical CTR metrics when passed to `compute_quality_metrics`.

**Actionable Verification Steps**:
1. This criterion is **fully verified** by existing automated tests.
2. Run `make test` to prove completion in the standard repo workflow.
3. Optional targeted fallback: `uv run pytest tests/unit/eval_platform/test_stage6_acceptance.py tests/unit/eval_platform/test_metrics.py::test_offline_reproducibility`.

## 3. Duplicate event submissions do not inflate CTR metrics.
**Objective**: Ensure idempotency works both at the database ingest level and the evaluator in-memory metric computation level so metrics are not double-counted.

**Current Coverage**:
- `tests/integration/test_telemetry_api.py::test_ingest_telemetry_events_duplicate_idempotency` proves the database rejects duplicates via `ON CONFLICT (idempotency_key) DO NOTHING`.
- `tests/unit/eval_platform/test_metrics.py::test_deduplication` proves the evaluator explicitly deduplicates events in-memory using `(event_type, idempotency_key)`, preserving the denominator (impressions) and numerator (clicks).

**Actionable Verification Steps**:
1. This criterion is **fully verified** by existing automated tests.
2. Run `make test` to prove completion in the standard repo workflow.
3. Optional targeted fallback: `uv run pytest tests/integration/test_telemetry_api.py tests/unit/eval_platform/test_metrics.py::test_deduplication`.

## 4. Report and summary clearly separate synthetic vs real telemetry.
**Objective**: Prevent synthetic evaluation telemetry from being misconstrued as real user telemetry by maintaining distinct visual and structural buckets.

**Current Coverage**:
- `tests/unit/eval_platform/test_metrics.py::test_traffic_splitting` verifies the `QualityMetrics` schema groups traffic into `synthetic`, `real`, and `combined` accurately based on the `is_synthetic` flag.
- `tests/unit/eval_platform/test_stage6_acceptance.py::test_stage6_acceptance_quality_metrics_integration` explicitly verifies that `summary.json` separates these buckets and that `report.md` contains distinct headings: `Traffic Type: Synthetic`, `Traffic Type: Real`, and `Traffic Type: Combined`.

**Actionable Verification Steps**:
1. This criterion is **fully verified** by existing automated tests.
2. Run `make test` to prove completion in the standard repo workflow.
3. Optional targeted fallback: `uv run pytest tests/unit/eval_platform/test_stage6_acceptance.py`.

## 5. Stage 3/4 hard gates remain unchanged; quality metrics remain soft.
**Objective**: Ensure that low or absent CTR metrics do not cause the evaluator to fail (exit code 1), while Stage 3/4 correctness/latency failures still do.

**Current Coverage**:
- `eval/evaluator.py` strictly exits with `1` only if `total_failed > 0` or `paired_regressions > 0`. Quality metrics are logged and computed but do not trigger a `sys.exit(1)`.
- `tests/unit/eval_platform/test_stage6_acceptance.py` explicitly catches `SystemExit` from the evaluator run to assert that `exc.code == 0` despite computing low/valid quality metrics.

**Actionable Verification Steps**:
1. This criterion is **verified for non-gating behavior in the Stage 6 quality-metrics path** by existing automated tests.
2. Run `make test` to prove completion in the standard repo workflow.
3. Optional targeted fallback: `uv run pytest tests/unit/eval_platform/test_stage6_acceptance.py`.

---
**Summary Statement**:
Criteria 2, 3, and 4 are fully implemented and verified via unit and integration tests. Criterion 5 is verified for non-gating behavior in the Stage 6 path. To definitively close out Criterion 1, implement the proposed integration test in `tests/integration/test_telemetry_api.py` to ensure `export_telemetry_extract` filters successfully by `run_id` in a live DB context.

## Done-Proof Sequence

1. Run `make test`.
2. Confirm the Criterion 1 export-filter integration test exists and passes.
3. Confirm the evidence map above has no remaining gaps marked for Stage 6 exit.
