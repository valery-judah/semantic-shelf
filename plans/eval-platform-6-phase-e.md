# Stage 6 Rollout Plan: Phase E (Compatibility Cleanup)

## Objective
Remove temporary transitional code related to legacy telemetry fields once all upstream systems have migrated to the new schema. Specifically, transitioning from `eval_run_id` to `run_id`.

## Prerequisites
- Phases A through D are deployed and verified.
- Confirmation that no client or loadgen tool is currently emitting `eval_run_id` instead of `run_id`.

## Implementation Steps

### 1. Audit Current Usage
- [ ] Search the API service layer (`src/books_rec_api/services/telemetry_service.py` and `src/books_rec_api/api/routes/telemetry.py`) for references to `eval_run_id`.
- [ ] Check telemetry logs to ensure no recent requests have triggered `eval_run_id` deprecation warnings (if logging was added).
- [ ] Confirm scope boundary: this cleanup targets telemetry payload compatibility only (`eval_run_id` event field). It does not rename request-context/header plumbing such as `X-Eval-Run-Id` or `eval_run_id_var`.

### 2. Code Removal
- [ ] Remove `eval_run_id` aliasing or mapping logic in the Telemetry schema (`src/books_rec_api/schemas/telemetry.py`).
- [ ] Ensure `run_id` is strictly enforced as required in Pydantic validation.
- [ ] Remove any associated deprecation log statements.

### 3. Testing
- [ ] Update API unit tests to verify that payloads containing only `eval_run_id` (and missing `run_id`) are now explicitly rejected with a 422 Validation Error.
- [ ] Update schema/unit tests to verify model validation fails when payloads provide `eval_run_id` without `run_id`.
- [ ] Run `make test` to ensure no regression in `run_id` processing.

## Acceptance Criteria
- `eval_run_id` compatibility is completely removed from the API schemas and services.
- The system exclusively enforces the `run_id` field.
- Payloads that omit `run_id` and send only `eval_run_id` are rejected with 422.
