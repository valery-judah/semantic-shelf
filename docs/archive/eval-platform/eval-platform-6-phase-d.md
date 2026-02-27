# Stage 6 Rollout Plan: Phase D (Report and Summary Integration)

## Objective
Ensure the computed quality metrics are correctly rendered in the markdown report and persisted in the `summary.json` schema, with clear separation between synthetic and real telemetry.

## Prerequisites
- Phase C (Evaluator Read + Export) is complete and verified.

## Implementation & Verification Steps

### 1. Schema Validation (`summary.json`)
- [x] Review `eval/schemas/summary.py` to ensure `QualityMetrics`, `MetricBucket`, and `QualityMetricsStatus` are fully defined and match actual output.
- [x] Run a test evaluation and verify `artifacts/eval/<run_id>/summary/summary.json` contains:
  - `quality_metrics` object.
  - `by_traffic_type` dictionary using canonical traffic buckets: `real`, `synthetic`, and `combined` (buckets may be absent only when no events exist for that bucket).
  - `ctr_at_k` and `ctr_by_position` properties.
  - Correct `quality_metrics_status` (e.g., `computed_from_db_then_exported`).

### 2. Report Rendering Validation (`report.md`)
- [x] Review `eval/rendering.py` generation logic for the Quality Metrics section.
- [x] Generate a report from an evaluation run and verify:
  - Section "Quality Metrics (Telemetry)" exists.
  - Traffic types (Synthetic vs. Real) are distinctly labeled.
  - Data sufficiency warnings appear correctly when impressions < 100.
  - Position curves are formatted cleanly as a markdown table.

### 3. CI Gate Behavior Check
- [x] Ensure that failures or changes in quality metrics (e.g., CTR dropping) do **not** cause the evaluator script to exit with a non-zero status code (hard gate).
- [x] Confirm quality metrics are treated as "soft signals" (info/warnings only) for Stage 6.

### 4. Integration Testing
- [x] Add or extend evaluator acceptance coverage under `tests/unit/eval_platform/` (for example in `test_evaluator.py` or a new `test_stage6_acceptance.py`) to assert end-to-end summary/report quality-metric integration.
- [x] If adding a dedicated Stage 6 file, keep scope explicit: report section presence, canonical `by_traffic_type` buckets (`real`, `synthetic`, `combined`) when corresponding events exist, and non-gating behavior.

## Acceptance Criteria
- Report and summary clearly separate synthetic vs real telemetry.
- Synthetic telemetry is visibly flagged.
- `quality_metrics.by_traffic_type` uses canonical traffic buckets (`real`, `synthetic`, `combined`) for telemetry presentation and comparison.
- Stage 3/4 hard gates remain unchanged; quality metrics remain soft (do not fail CI).
