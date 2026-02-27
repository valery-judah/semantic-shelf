# Plan: Stage 6 - Section 7.2 Contract Finalization (No Compatibility Path)

## Overview

This plan replaces the prior compatibility transition work for section 7.2. Since MVP has a single producer, we will move directly to the strict Stage 6 contract:

- telemetry events must provide `run_id`
- `eval_run_id` is not accepted

The goal is to keep ingestion behavior explicit and predictable, avoiding temporary alias logic.

## Actionable Steps

- [ ] **Finalize Contract Documentation**
  Update `docs/eval-platform-6.md` to remove the transition compatibility requirement (`eval_run_id` -> `run_id`) and state that `run_id` is required with no alias support.

- [ ] **Confirm Schema Strictness**
  Keep `TelemetryEventBase` in `src/books_rec_api/schemas/telemetry.py` strict: no compatibility validator, no field aliasing for `eval_run_id`, and validation continues to require non-empty `run_id`.

- [ ] **Keep Rejection Tests Explicit**
  Preserve and clarify tests that prove old payloads are rejected:
  - `tests/unit/test_telemetry.py::test_event_with_eval_run_id_only_is_rejected`
  - `tests/integration/test_telemetry_api.py::test_ingest_telemetry_events_rejects_eval_run_id_only_payload`

- [ ] **Run Required Checks**
  Because this is API/schema behavior, run the full required check set:
  - `make fmt`
  - `make lint`
  - `make type`
  - `make test`
