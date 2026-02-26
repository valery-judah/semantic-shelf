# Domain Modeling Plan for Eval Anchors

## Context
This plan is the anchor-specific execution track under:
- [docs/eval-domain-centralization.md](/Users/val/ml/projects/books-rec/semantic-shelf/docs/eval-domain-centralization.md)
- [plans/eval-domain-centralization-implementation.md](/Users/val/ml/projects/books-rec/semantic-shelf/plans/eval-domain-centralization-implementation.md)

It focuses only on refactoring `eval/anchors.py` and related tests/callers with compatibility-first constraints.

## Scope

### In Scope
- Anchor selection domain modeling and error semantics.
- Golden set I/O boundary extraction for anchors.
- Anchor selection input validation policy.
- Test updates for deterministic behavior and compatibility.

### Out of Scope
- Global eval schema redesign.
- Non-anchor evaluator pipeline changes.
- Artifact schema migration beyond anchor fields in `raw/anchors.json`.

## Compatibility Contract
- Preserve `raw/anchors.json` fields in Phase A:
  - `anchors: list[str]`
  - `anchor_metadata: dict[str, dict[str, Any]]`
- Keep orchestrator write path behavior unchanged.
- Domain exceptions must inherit from `ValueError` in Phase A.

## Implementation

### 1. Domain Types and Errors
- Add `eval/domain.py` value types:
  - `DatasetId`, `ScenarioId`, `AnchorId`, `GoldenId`
- Add `eval/errors.py` with:
  - `AnchorDomainError(ValueError)`
  - `AnchorNotFoundError`
  - `ScenarioMismatchError`
  - `GoldenSetNotFoundError` (if needed)

### 2. Internal Anchor Entity + Mapping Boundary
- Represent selected anchors internally as typed entities (e.g., `Anchor(id, metadata)`).
- Keep public function boundary in `eval/anchors.py` unchanged for Phase A.
- Convert internal entities to wire shape at the boundary.

### 3. Golden Repository Boundary
- Move filesystem-specific golden loading out of selection logic into a loader/repository abstraction.
- Keep selection/shuffle logic pure and deterministic.

### 4. Validation Policy for `count`
Choose one policy explicitly before merging:
1. Compatibility policy: `count <= 0` returns empty output.
2. Strict policy: `count < 0` is invalid and raises validation error.

If strict policy is chosen:
- document behavior change in this plan and related docs,
- update orchestrator error-path expectations,
- add tests that lock the new behavior.

### 5. Test Plan
Update/add tests in:
- `tests/unit/eval_platform/test_anchors.py`
- `tests/unit/eval_platform/test_eval_orchestrator.py`

Required cases:
- deterministic selection for same inputs,
- different seed produces different order,
- scenario mismatch uses domain-specific exception,
- `ValueError` compatibility remains true,
- `count` policy behavior is explicit and covered,
- orchestrator still writes compatible `raw/anchors.json`.

## Rollout

### Phase A (Required, Non-Breaking)
- Complete steps 1-5 above.
- Do not change serialized anchor field names or layout.

### Phase B (Optional, Versioned)
- Only if structured anchor serialization is needed:
  - bump `anchors_schema_version`,
  - implement transition support (dual-read or migration),
  - update docs and consumers before old-format removal.

## Definition of Done

### Phase A
1. Anchor domain types/errors are implemented and used.
2. Golden set I/O is separated from pure selection logic.
3. `raw/anchors.json` remains backward compatible.
4. Tests cover behavior and compatibility requirements.
5. Quality gates pass:
   - `make fmt`
   - `make lint`
   - `make type`
   - `make test`

### Phase B (If Executed)
1. Schema versioning and migration path are explicit.
2. Consumers and tests are updated for the new format.
3. Quality gates pass:
   - `make fmt`
   - `make lint`
   - `make type`
   - `make test`
