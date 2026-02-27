# Implementation Plan: Eval Platform Stage 6, Step 3

This document outlines the implementation plan for the remainder of **Step 3 (API and Service Layer Changes)** from `docs/eval-platform-6.md`.

## Context and Current State

Based on `docs/eval-platform-6.md` and the current codebase state, most of Step 3 is already implemented, specifically:
- Schema validation and explicit schema-to-row mapping
- Bulk insert of accepted events with conflict-safe idempotency (`ON CONFLICT (idempotency_key) DO NOTHING`)
- Emitting structured ingest summary logs

The remaining requirement for Step 3 is the **run-scoped read API for the evaluator export path (pending)**.

## Goal

Provide a run-scoped read API for the evaluator that returns normalized, typed records used for Stage 6 quality metrics computation (initially `similar_impression` and `similar_click`).

## Implementation Steps

### 1. Update `TelemetryRepository` (`src/books_rec_api/repositories/telemetry_repository.py`)
- Implement `get_events_by_run_id(self, run_id: str, event_names: Sequence[str] | None = None) -> list[EvalTelemetryEvent]`.
- Query the SQLAlchemy `TelemetryEvent` model filtered by `run_id == run_id`, ordered by `ts`.
- For evaluator usage, filter to metric-relevant event names (`similar_impression`, `similar_click`) by default.
- Implement a private helper method (for example, `_to_eval_event`) that maps DB rows to evaluator read models, not the full ingest union.

### 2. Update Repository Tests (`tests/unit/test_telemetry_repository.py`)
- Add a test `test_get_events_by_run_id_returns_correct_events` to insert mixed event types (impression, click, and at least one non-metric event) and ensure only evaluator-relevant events are returned as typed records.
- Assert ordering by `ts`.
- Add a test `test_get_events_by_run_id_returns_empty_list_when_no_match` to ensure the repository safely handles a missing `run_id`.

### 3. Update `TelemetryService` (`src/books_rec_api/services/telemetry_service.py`)
- Expose the read API via `get_events_by_run_id(self, run_id: str, event_names: Sequence[str] | None = None) -> list[EvalTelemetryEvent]`.
- This delegates to `self._repo.get_events_by_run_id(run_id)`, exposing the functionality and isolating the evaluator from direct DB session management.

### 4. Update Service Tests (`tests/unit/test_telemetry.py`)
- Add tests to verify that the service cleanly forwards requests to the mocked repository and returns the correct schema instances when fetching by `run_id`.

## Acceptance Criteria
- `TelemetryRepository` and `TelemetryService` expose `get_events_by_run_id`.
- The returned objects are evaluator-typed records for metric computation (initially impression and click events only).
- The read path supports deterministic evaluator export inputs for `raw/telemetry_extract.jsonl`.
- `make test` runs cleanly and incorporates the new test coverage.
