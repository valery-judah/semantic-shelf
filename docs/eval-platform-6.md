# Stage 6 Implementation Plan: Telemetry Contract and Storage

## Overview

This document defines the implementation plan for Stage 6 from `docs/eval-platform-staged.md`, using architecture and principles from `docs/eval-platform.md`.

Stage 6 objective: establish a strict, run-attributable telemetry contract and durable storage so quality metrics (starting with CTR@K and position curves) are reproducible and safe to interpret.

## Stage 6 Scope and Principles

Stage 6 is constrained by these principles from `docs/eval-platform.md`:

1. Run identity is non-negotiable: telemetry must be filterable by `run_id`.
2. Artifacts are the source of truth: evaluator outputs must be reproducible from persisted data.
3. Stable schemas over ad-hoc parsing: telemetry and summary payloads are versioned and validated.
4. Debuggability is part of the contract: every metric must have a triage path.
5. Incremental complexity: Stage 6 enables quality metrics plumbing; hard quality gating remains Stage 7+

## Current-State Gaps

Current repo behavior (as of this plan):

- `/telemetry/events` validates event payloads, then writes JSON to logs only.
- Telemetry schema lacks required Stage 6 fields such as `telemetry_schema_version`, `run_id`, `arm`, `is_synthetic`, and idempotency key.
- No `telemetry_events` table exists in SQLAlchemy models or migrations.
- Evaluator does not read telemetry or export telemetry extracts.
- `summary/summary.json` has no quality-metrics section.

## Target Stage 6 Capabilities

After Stage 6 completion:

- Evaluator can query telemetry strictly by `run_id` and compute CTR@K + position curves.
- Duplicate writes do not inflate metrics due to idempotency constraints.
- Synthetic telemetry is explicitly marked and separated in report/summary.
- Evaluator can export `raw/telemetry_extract.jsonl` for full offline reproducibility.

## Implementation Design

## 1) Telemetry Contract v1

### 1.1 Schema additions

Update `src/books_rec_api/schemas/telemetry.py` to enforce a versioned event contract.

Required base fields for all telemetry events:

- `telemetry_schema_version` (literal `"1.0.0"` for this stage)
- `event_name`
- `ts`
- `run_id`
- `request_id`
- `surface`
- `arm` (`baseline`, `candidate`, `unknown`)
- `anchor_book_id`
- `is_synthetic`
- `idempotency_key`

Event-specific fields:

- Impression: `shown_book_ids`, `positions`
- Click: `clicked_book_id`, `position`
- Optional downstream events can remain accepted but are out-of-scope for Stage 6 metrics.

Validation rules:

- `shown_book_ids` length equals `positions` length.
- positions are non-negative.
- click `position` is non-negative.
- `request_id` and `run_id` are non-empty strings.
- `idempotency_key` is non-empty and deterministic for retries.

### 1.2 Compatibility plan (`eval_run_id` -> `run_id`)

If any existing producers use `eval_run_id`:

- API accepts `eval_run_id` during transition window.
- Service canonicalizes to `run_id` before persistence.
- Add deprecation log warning when `eval_run_id` is seen.
- Remove compatibility path after one release cycle.

## 2) Storage Model and DB Migration

### 2.1 New table

Add `telemetry_events` table with explicit columns (not JSON blob only):

- identity: `id` (bigserial), `telemetry_schema_version`
- attribution: `run_id`, `request_id`, `surface`, `arm`, `event_name`, `is_synthetic`
- event time: `ts`
- content: `anchor_book_id`, `shown_book_ids` (JSON), `positions` (JSON), `clicked_book_id`, `position`
- dedupe: `idempotency_key`
- ingest metadata: `ingested_at`

### 2.2 Indices and constraints

Required indices:

- `idx_telemetry_events_run_id` on `(run_id)`
- `idx_telemetry_events_run_event` on `(run_id, event_name)`
- `idx_telemetry_events_request_id` on `(request_id)`

Required uniqueness:

- `uq_telemetry_events_idempotency_key` unique on `idempotency_key`

### 2.3 Write semantics

Use insert with conflict handling for idempotency:

- `ON CONFLICT (idempotency_key) DO NOTHING`
- Return inserted count vs duplicate count for observability.

## 3) API and Service Layer Changes

### 3.1 Route contract

`src/books_rec_api/api/routes/telemetry.py` remains `POST /telemetry/events` but behavior changes:

- Persist validated events in `telemetry_events`.
- Keep structured logs for diagnostics, but DB is now source for evaluator queries.
- Response remains `202 accepted` with optional counts.

### 3.2 Service and repository

Add repository for telemetry persistence (new module):

- bulk insert accepted events
- conflict-safe idempotency handling
- run-scoped read API for evaluator export path

Update service (`TelemetryService`) responsibilities:

- validation stays at schema layer
- canonicalize compatibility fields
- map schema -> DB row
- call repository bulk insert
- emit structured ingest summary logs

## 4) Eval Loadgen Integration for Synthetic Telemetry

Stage 6 needs deterministic synthetic events for eval runs while real telemetry matures.

### 4.1 Scenario config extension

Extend `eval/schemas/scenario.py` with optional telemetry block:

- `emit_telemetry: bool`
- `telemetry_mode: synthetic | none`
- `click_model: none | first_result | fixed_ctr`
- `fixed_ctr` configuration where relevant

### 4.2 Loadgen emission

In `eval/loadgen.py`:

- after each successful similar-books response, emit `similar_impression`
- optionally emit `similar_click` based on configured synthetic click model
- include `run_id`, `request_id`, `surface`, `arm`, `is_synthetic=true`
- set deterministic `idempotency_key` per logical event

Paired mode:

- ensure arm-specific events are emitted with arm preserved from request record.

## 5) Evaluator Integration

### 5.1 Telemetry reader

Add evaluator telemetry reader module in `eval/`:

- query `telemetry_events` by `run_id`
- optionally restrict to surface/event names for scenario
- return normalized typed records for metrics computation

### 5.2 Artifact export

Evaluator writes `artifacts/eval/<run_id>/raw/telemetry_extract.jsonl` with rows used in metric computation.

This file is the reproducibility boundary for CTR calculations.

### 5.3 Metrics and summary schema

Extend `eval/schemas/summary.py` with a quality section (schema version bump):

- telemetry coverage counts (`impressions`, `clicks`, deduped counts)
- `ctr_at_k` (initially K=10, configurable)
- position curve (`ctr_by_position`)
- synthetic/real split

Report updates in `eval/rendering.py`:

- include telemetry section with synthetic vs real labels
- include data sufficiency notes (e.g., low-volume warning)

## 6) Rollout Strategy

### Phase A: Contract and storage foundation

- add schema fields + migration + repository + service persistence
- keep evaluator unchanged
- verify ingestion correctness and idempotency

### Phase B: Synthetic telemetry emission

- add scenario/loadgen telemetry hooks
- generate synthetic events for eval scenarios

### Phase C: Evaluator read + export

- compute CTR@K and position curves from DB query by `run_id`
- emit `telemetry_extract.jsonl`

### Phase D: Report and summary integration

- add quality section to summary/report
- keep quality as soft signal (no hard CI gate)

### Phase E: Compatibility cleanup

- remove `eval_run_id` compatibility once all producers migrated

## 7) Testing Plan

## 7.1 Unit tests

- telemetry schema validation and discriminated unions
- idempotency conflict handling in repository
- summary quality schema validation
- CTR and position metric calculations from fixture events

## 7.2 Integration tests

- `POST /telemetry/events` persists rows and returns accepted
- duplicate event posts do not increase row count
- compatibility input (`eval_run_id`) maps to `run_id` during transition

## 7.3 Eval-platform tests

- end-to-end run emits synthetic telemetry and evaluator writes telemetry extract
- recompute CTR from extract equals summary CTR
- synthetic telemetry clearly flagged in report/summary

## 8) Acceptance Criteria (Stage Exit)

Stage 6 is done when all are true:

1. Evaluator computes CTR@K from telemetry queried by `run_id` only.
2. Recomputed CTR@K from `raw/telemetry_extract.jsonl` matches summary output.
3. Duplicate event submissions do not inflate CTR metrics.
4. Report and summary clearly separate synthetic vs real telemetry.
5. Stage 3/4 hard gates remain unchanged; quality metrics remain soft.

## 9) File-Level Change Plan

Primary files expected to change:

- `src/books_rec_api/schemas/telemetry.py`
- `src/books_rec_api/services/telemetry_service.py`
- `src/books_rec_api/api/routes/telemetry.py`
- `src/books_rec_api/models.py`
- `migrations/versions/<new_revision>_add_telemetry_events.py`
- `eval/schemas/scenario.py`
- `eval/loadgen.py`
- `eval/evaluator.py`
- `eval/metrics.py`
- `eval/schemas/summary.py`
- `eval/rendering.py`
- `tests/unit/test_telemetry.py`
- `tests/integration/test_telemetry_api.py`
- `tests/unit/eval_platform/test_evaluator.py`
- `tests/unit/eval_platform/test_schemas.py`
- docs references (`docs/eval-platform-staged.md` only if status checkboxes are maintained)

## 10) Risks and Mitigations

- Risk: synthetic events are interpreted as product truth.
- Mitigation: mandatory `is_synthetic`; separate report section; no hard gate.

- Risk: event duplication inflates metrics.
- Mitigation: unique `idempotency_key` + conflict-safe writes + duplicate-rate diagnostics.

- Risk: schema churn breaks producers.
- Mitigation: versioned schema and temporary compatibility path.

- Risk: evaluator/DB coupling harms local reproducibility.
- Mitigation: always export `telemetry_extract.jsonl` and allow offline recomputation from extract.

## 11) Done Checklist

- [x] Telemetry schema v1 implemented and validated
- [ ] `telemetry_events` table + indices + unique constraint added
- [ ] idempotent DB writes implemented
- [ ] loadgen synthetic telemetry emission implemented
- [ ] evaluator telemetry query by `run_id` implemented
- [ ] `raw/telemetry_extract.jsonl` generated
- [ ] summary/report quality section added
- [ ] tests added/updated and passing (`make test`)
- [ ] docs updated where Stage 6 completion state is tracked
