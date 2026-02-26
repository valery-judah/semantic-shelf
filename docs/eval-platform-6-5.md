# Stage 6, Step 5: Evaluator Integration Implementation Plan

This document outlines the detailed implementation plan for Step 5 (Evaluator Integration) of the Telemetry Contract and Storage implementation (Stage 6), per the guidelines in `docs/eval-platform.md` and `docs/eval-platform-6.md`.

## Objective
Enable the Evaluator to query run-specific telemetry data, compute quality metrics (such as CTR@K and position curves), guarantee offline reproducibility via a telemetry extract artifact, and separate real vs. synthetic traffic in final reports.

## Detailed Steps

### 1. Telemetry Reader & Extractor (`eval/telemetry.py`)
Create a new module to handle retrieving telemetry from the `telemetry_events` table and exporting it.
*   **Database Querying**: Implement a reader (using `psycopg` or `sqlalchemy`, similar to other evaluator read access) to fetch all rows matching a specific `run_id`.
*   **Artifact Export**: Create a function `export_telemetry_extract(run_id: str, base_dir: Path)` to dump the fetched rows into `artifacts/eval/<run_id>/raw/telemetry_extract.jsonl`. This file becomes the reproducibility boundary for metric calculations, preventing hidden coupling to the live database.
*   **Data Normalization**: Parse the raw rows/extracts into typed Pydantic models (e.g., `TelemetryEvent` encompassing `similar_impression` and `similar_click`) that can be consumed by the metrics computation pipeline.

### 2. Metrics and Summary Schema Update (`eval/schemas/summary.py`)
Extend the current `RunSummary` schema to include quality metrics.
*   **Schema Version Bump**: Update `summary_schema_version` (e.g., to `"1.1.0"` or appropriate next version).
*   **New `QualityMetrics` Model**: Add split-aware metrics so mixed traffic runs are representable without lossy aggregation.
    *   `k`: Configured K for CTR@K (default 10).
    *   `by_traffic_type`: Object with `real`, `synthetic`, and optional `combined` metric buckets.
    *   Each bucket includes:
        *   `impressions`: Total valid impression events.
        *   `clicks`: Total valid click events.
        *   `ctr_at_k`: Float CTR up to K.
        *   `ctr_by_position`: Mapping from position index (0-indexed) to CTR.
        *   `coverage`: Counts needed for interpretability (for example, impressions_with_position_lt_k, matched_clicks).
*   **Computation Provenance**: Add explicit status metadata in summary:
    *   `quality_metrics_status`: enum such as `computed_from_extract`, `computed_from_db_then_exported`, `no_telemetry`.
    *   `quality_metrics_notes`: optional list of warnings (low volume, malformed events dropped, etc.).

### 3. Metric Computation Pipeline (`eval/metrics.py`)
Extend the evaluation pipeline to process the extracted telemetry.
*   **Canonical Input**: Compute metrics from normalized events loaded from `telemetry_extract.jsonl`; DB rows are only a source for creating that extract when needed.
*   **CTR Calculation**: Write functions to compute overall CTR, CTR@K, and CTR by position from normalized `TelemetryEvent` models.
*   **Formula Contract**: Document and enforce exact formulas:
    *   `ctr_at_k = matched_clicks_at_positions_lt_k / impressions_with_position_lt_k`.
    *   `ctr_by_position[p] = clicks_at_position_p / impressions_at_position_p`.
*   **Attribution Rule**: Define click-to-impression matching rule (for example by `request_id`, `anchor_book_id`, `clicked_book_id`, and `position`) and use the same rule in live compute and replay.
*   **Synthetic vs. Real Split**: Partition metrics strictly by telemetry `is_synthetic` with optional `combined` roll-up.
*   **Deduplication Policy**: Treat DB uniqueness on `idempotency_key` as canonical dedupe; evaluator-side dedupe is defensive-only and must be deterministic and documented.

### 4. Evaluator Orchestration (`eval/evaluator.py`)
Wire the new reader and metrics into the main evaluator process.
*   **Source Precedence (Required)**:
    1. If `artifacts/eval/<run_id>/raw/telemetry_extract.jsonl` already exists, read it and compute metrics directly.
    2. Else query DB by `run_id`, export `telemetry_extract.jsonl`, then compute metrics from the exported file.
    3. If neither source is available, emit empty quality metrics with `quality_metrics_status = no_telemetry`.
*   **Fetch & Export**: During evaluator run, call `export_telemetry_extract` only when extract is missing.
*   **Metric Computation**: Call functions in `eval/metrics.py` using extract-loaded events only, so live and offline paths are identical.
*   **Summary Integration**: Attach the newly computed `QualityMetrics` to the final `RunSummary` object before writing it to `summary/summary.json`.
*   **Graceful Degradation**: If DB is unavailable but extract exists, continue from extract; if no usable telemetry source exists, continue without crashing and emit explicit status/warnings.

### 5. Report Rendering (`eval/rendering.py`)
Update the Markdown report generation to surface the new quality metrics.
*   **New Section**: Add a "Quality Metrics (Telemetry)" section to `report.md`.
*   **Visibility and Clarity**: Explicitly label whether the metrics are "Synthetic" (generated by loadgen) or "Real", preventing synthetic data from being mistaken for product truth.
*   **Data Sufficiency Warnings**: Add a warning note if the volume of telemetry data is too low to be statistically significant (e.g., `< 100` impressions).
*   **Position Curves**: Render a simple markdown table or textual representation of the `ctr_by_position` curve.

### 6. Testing (`tests/unit/eval_platform/`)
Add unit and integration tests for the new components.
*   **`test_telemetry.py` (eval evaluator)**: Test extraction logic, ensuring `telemetry_extract.jsonl` matches expected outputs and extract-read precedence works.
*   **`test_metrics.py`**: Test CTR@K formulas, position curve calculations, and click/impression attribution join rules using mocked telemetry fixtures.
*   **`test_schemas.py`**: Validate the updated `RunSummary` and `QualityMetrics` schemas.
*   **`test_evaluator.py`**: Test end-to-end integration, verifying:
    *   mixed real + synthetic events are split correctly,
    *   DB unavailable + existing extract still computes quality metrics,
    *   recompute from extract matches summary output exactly,
    *   duplicate submissions cannot inflate reported CTR.

## Acceptance Criteria Check
*   [ ] Evaluator computes CTR@K from telemetry queried by `run_id` only.
*   [ ] Recomputed CTR@K from `raw/telemetry_extract.jsonl` matches summary output.
*   [ ] Duplicate event submissions do not inflate CTR metrics.
*   [ ] Report and summary clearly separate synthetic vs real telemetry.
*   [ ] Summary includes explicit quality metric provenance/status (`computed_from_extract`, `computed_from_db_then_exported`, or `no_telemetry`).
*   [ ] Stage 3/4 hard gates remain unchanged; quality metrics remain soft.
