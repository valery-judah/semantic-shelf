# Eval Domain Centralization Implementation Plan

## Objective
Implement a centralized and systemic eval domain view while preserving current artifact contracts in the initial rollout.

## Principles
- Compatibility first.
- Domain and I/O boundaries are explicit.
- Wire schemas remain authoritative for persisted payloads.
- Behavior changes are intentional, documented, and tested.

## Phase A: Non-Breaking Refactor

### A1. Introduce Domain Primitives
Create:
- `eval/domain.py`
  - `DatasetId`, `ScenarioId`, `AnchorId`, `GoldenId` via `NewType`

### A2. Introduce Domain Errors
Create:
- `eval/errors.py`
  - `AnchorDomainError(ValueError)`
  - `AnchorNotFoundError(AnchorDomainError)`
  - `ScenarioMismatchError(AnchorDomainError)`
  - `GoldenSetNotFoundError(AnchorDomainError)` (if needed)

### A3. Isolate Golden Set I/O
Create:
- `eval/golden_repository.py` (or equivalent)

Responsibilities:
- resolve golden path
- read and parse golden JSON into `GoldenSet`
- raise domain errors for not found/invalid inputs

### A4. Extract Pure Selection Logic
Refactor:
- `eval/anchors.py`

Changes:
- Keep public output `(anchors, anchor_metadata)` unchanged.
- Move deterministic selection/shuffle into pure functions operating on domain entities.
- Keep boundary mapping explicit and local.

### A5. Clarify Count Validation Policy
Choose one policy and codify it:
- Option 1: keep `count <= 0` => empty selection (fully compatible)
- Option 2: enforce `count >= 0` (intentional behavior change)

If Option 2:
- update orchestrator error expectations
- add migration note in docs

### A6. Tests
Update/add:
- `tests/unit/eval_platform/test_anchors.py`
  - deterministic behavior
  - scenario mismatch and missing golden behavior
  - domain exception specificity
  - `ValueError` compatibility catch behavior
  - selected count policy coverage
- `tests/unit/eval_platform/test_eval_orchestrator.py`
  - validate unchanged `raw/anchors.json` contract

### A7. Documentation
Update:
- `plans/domain-modeling-eval-anchors.md` (already aligned)
- any relevant stage docs if policy changes (count semantics, exceptions)

## Phase B: Optional Schema Evolution

### B1. Decide New Anchor Wire Shape
If needed, define a new schema form in `eval/schemas/raw.py` with explicit version bump.

### B2. Transition Strategy
Implement one:
- dual-read support, or
- migration utility and strict cutover date

### B3. Consumer and Doc Updates
- update orchestrator/evaluator readers
- add schema migration tests
- update docs that describe artifact contracts

## Acceptance Criteria

### Phase A
1. Domain primitives and domain errors exist and are used in anchor flow.
2. Golden set loading is isolated from selection logic.
3. Existing `raw/anchors.json` shape remains unchanged.
4. Existing consumer paths remain functional.
5. Tests cover compatibility and new domain boundaries.
6. Checks pass:
   - `make fmt`
   - `make lint`
   - `make type`
   - `make test`

### Phase B (if executed)
1. Schema changes are versioned and documented.
2. Compatibility transition is implemented and tested.
3. Consumers and docs are updated before old format removal.
4. Checks pass:
   - `make fmt`
   - `make lint`
   - `make type`
   - `make test`

## Risks and Mitigations
- Risk: hidden consumer dependency on current anchor payload fields.
  - Mitigation: keep Phase A payload unchanged; add contract tests.
- Risk: exception hierarchy change breaks callers.
  - Mitigation: subclass `ValueError` during migration.
- Risk: behavior drift from count validation changes.
  - Mitigation: decide policy explicitly and lock with tests.

## Proposed Sequence
1. Add domain primitives and errors.
2. Add repository boundary.
3. Refactor selection logic.
4. Update tests and verify contract stability.
5. Run full quality gate.
