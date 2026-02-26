# Stage 6 Implementation Plan: Step 4 - Eval Loadgen Integration for Synthetic Telemetry

## Overview
This document outlines the implementation plan for Step 4 of the Stage 6 telemetry integration, focusing on extending the loadgen to emit deterministic, synthetic telemetry events. This allows the evaluator to measure quality metrics (CTR@K, position curves) based on run-attributable telemetry even before organic telemetry matures.

## 1. Scenario Config Extension (`eval/schemas/scenario.py`)
Extend `ScenarioConfig` to support an optional `telemetry` block.

**Changes:**
- Add a new Pydantic model `TelemetryConfig`:
  - `emit_telemetry`: `bool` (default: `False`)
  - `telemetry_mode`: `Literal["synthetic", "none"]` (default: `"none"`)
  - `click_model`: `Literal["none", "first_result", "fixed_ctr"]` (default: `"none"`)
  - `fixed_ctr`: `float | None` (default: `None`)
- Add a `@model_validator` to `TelemetryConfig` ensuring `fixed_ctr` is not `None` when `click_model` is `"fixed_ctr"`.
- Add `telemetry: TelemetryConfig | None = None` to the `ScenarioConfig` model.

## 2. Loadgen Emission (`eval/loadgen.py`)
Update `execute_request` to parse successful API responses and emit `similar_impression` and optional `similar_click` telemetry events asynchronously.

**Changes:**
- **Condition:** After successful response validation (`failure_type is None`), check if `scenario_config.telemetry` is defined and `emit_telemetry` is `True`.
- **Extraction:** Extract `similar_book_ids`, `algo_id`, and `recs_version` from the `response.json()` payload.
- **Event Construction:**
  - Build a `similar_impression` event. Include evaluation context: `run_id`, `request_id`, `arm` (or `"unknown"`), `is_synthetic=True`. Map `similar_book_ids` to `shown_book_ids` and set `positions` using 0-based indexing. Assign an `idempotency_key` (e.g., `f"imp_{request_id}"`).
  - Depending on `click_model`:
    - `"first_result"`: Create a `similar_click` event for the 0th position book with `idempotency_key` (e.g., `f"click_{request_id}"`).
    - `"fixed_ctr"`: Deterministically hash the `request_id` and compare against `fixed_ctr` to probabilistically decide if a `similar_click` event should be appended.
- **Emission:** 
  - Send the constructed `events` array via `await client.post(f"{api_url}/telemetry/events", json={"events": events}, ...)` within a broad `try-except` block.
  - Doing this after computing the main request `latency_ms` guarantees that telemetry overhead does not skew load test performance metrics.

## 3. Unit Test Updates (`tests/unit/eval_platform/test_loadgen.py`)
Update the test suite to validate the new synthetic telemetry logic.

**Changes:**
- Update existing asynchronous test mocks by adding `mock_client.post = AsyncMock()` so `MagicMock(spec=httpx.AsyncClient)` intercepts the telemetry emission gracefully.
- Add specific unit tests to verify that `similar_impression` and `similar_click` batch objects are constructed correctly based on `telemetry_mode` (`"first_result"` and `"fixed_ctr"`).

## 4. Acceptance and Rollout
- Execute `make test` locally to ensure regression and unit tests pass.
- In subsequent steps, synthetic scenarios (e.g., `similar_books_smoke.yaml`) can safely be updated to include the `telemetry` config block.
