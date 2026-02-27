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
- Add a `@model_validator` to `TelemetryConfig`:
  - ensure `fixed_ctr` is not `None` when `click_model` is `"fixed_ctr"`
  - ensure `fixed_ctr` is within `[0.0, 1.0]` when provided
- Add `telemetry: TelemetryConfig | None = None` to the `ScenarioConfig` model.

## 2. Loadgen Emission (`eval/loadgen.py`)
Update `execute_request` to parse successful API responses and emit `similar_impression` and optional `similar_click` telemetry events asynchronously.

**Changes:**
- **Condition:** After successful response validation (`failure_type is None`), emit telemetry only when:
  - `scenario_config.telemetry` is defined
  - `emit_telemetry` is `True`
  - `telemetry_mode` is `"synthetic"`
- **Extraction:** Extract `similar_book_ids`, `algo_id`, and `recs_version` from the `response.json()` payload.
- **Event Construction:**
  - Build a `similar_impression` event. Include all required telemetry fields:
    - base fields: `telemetry_schema_version="1.0.0"`, `ts` (UTC), `event_name`, `run_id`, `request_id`, `surface`, `arm` (or `"unknown"`), `anchor_book_id`, `is_synthetic=True`, `idempotency_key`
    - rec metadata: `algo_id`, `recs_version`
    - impression payload: map `similar_book_ids` to `shown_book_ids` and set `positions` using 0-based indexing
  - Use deterministic, event-specific idempotency keys (for example, `imp_{request_id}` and `click_{request_id}`).
  - Depending on `click_model`:
    - `"first_result"`: if `similar_book_ids` is non-empty, create a `similar_click` event for the 0th position book; otherwise skip click emission.
    - `"fixed_ctr"`: deterministically hash `request_id` and compare against `fixed_ctr` to decide click emission. If selected, only emit when `similar_book_ids` is non-empty.
- **Emission:** 
  - Send the constructed `events` array via `await client.post(f"{api_url}/telemetry/events", json={"events": events}, ...)` within a broad `try-except` block.
  - Doing this after computing the main request `latency_ms` guarantees that telemetry overhead does not skew load test performance metrics.

## 3. Unit Test Updates (`tests/unit/eval_platform/test_loadgen.py`)
Update the test suite to validate the new synthetic telemetry logic.

**Changes:**
- Update existing asynchronous test mocks by adding `mock_client.post = AsyncMock()` so `MagicMock(spec=httpx.AsyncClient)` intercepts the telemetry emission gracefully.
- Add specific unit tests to verify that `similar_impression` and `similar_click` batch objects are constructed correctly based on `click_model` (`"first_result"` and `"fixed_ctr"`).
- Add tests that assert emitted event payloads include required telemetry base fields (`ts`, `surface`, `anchor_book_id`, `algo_id`, `recs_version`, and deterministic `idempotency_key`).
- Add tests for edge cases:
  - empty `similar_book_ids` does not emit click events
  - invalid `fixed_ctr` values fail config validation

## 4. Acceptance and Rollout
- Execute `make test` locally to ensure regression and unit tests pass.
- In subsequent steps, synthetic scenarios (e.g., `similar_books_smoke.yaml`) can safely be updated to include the `telemetry` config block.
