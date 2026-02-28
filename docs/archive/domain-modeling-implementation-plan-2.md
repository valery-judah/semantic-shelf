# Domain Modeling: Implementation Plan 2

## Goal
Move domain primitives from `NewType` aliases to dataclass value objects with explicit runtime constraints, while preserving API and artifact contracts.

## Scope
- `src/books_rec_api/domain.py`
- `src/books_rec_api/services/*`
- `src/books_rec_api/repositories/*`
- `eval/domain.py`
- `eval/anchors.py`
- related tests and docs

## Principles
- Keep Pydantic models as the wire/schema boundary for API and persisted eval artifacts.
- Move domain invariants into explicit domain constructors (`__post_init__` or factory methods).
- Preserve behavior and response shapes unless a change is intentionally declared.
- Roll out in small slices with passing checks at each slice.

## Rollout Plan
1. Keep wire boundaries unchanged.
- Continue using existing schema modules for API I/O and artifact contracts:
  - `src/books_rec_api/schemas/*`
  - `eval/schemas/*`
- Do not change field names, required/optional semantics, or schema versions in this step.

2. Introduce dataclass value objects in API domain.
- Replace `NewType` aliases in `src/books_rec_api/domain.py` with frozen dataclasses (slots enabled).
- Add runtime constraints in `__post_init__` (or a small shared validator utility), for example:
  - ID non-empty checks
  - `InternalUserId` pattern checks
  - `Score` range checks
- Provide ergonomic conversion helpers (`__str__`, or `to_raw()` methods) for boundary mapping.

3. Add explicit service mapping boundaries.
- In services, map external/schema values to domain dataclasses on input.
- Map domain dataclasses back to schema/raw values on output.
- Primary files:
  - `src/books_rec_api/services/user_service.py`
  - `src/books_rec_api/services/book_service.py`

4. Update repository/service signatures incrementally.
- Replace primitive signatures with domain dataclass types where feasible.
- Keep SQLAlchemy model interactions and persisted DB payloads unchanged.
- Primary files:
  - `src/books_rec_api/repositories/users_repository.py`
  - `src/books_rec_api/repositories/books_repository.py`
  - `src/books_rec_api/services/user_service.py`
  - `src/books_rec_api/services/book_service.py`

5. Reduce implicit validation coupling.
- Remove or minimize reliance on `@validate_call` for domain invariants.
- Keep method typing and schema validation at boundaries, but enforce core invariants in domain constructors.

6. Mirror the approach in eval domain.
- Migrate `eval/domain.py` IDs from `NewType` to dataclass value objects.
- Keep `eval/anchors.py` and orchestrator output behavior compatible with current artifact contracts.

7. Roll out by type family (small PRs).
- PR 1: IDs only (`BookId`, `InternalUserId`, `ExternalIdpId`, eval IDs).
- PR 2: scoring/version/algo types (`Score`, `AlgoId`, `RecsVersion`).
- PR 3: repository and service signatures/mappers.
- PR 4: cleanup (remove obsolete adapters and dead code).

## Testing and Validation
- For code changes, run:
  1. `make fmt`
  2. `make lint`
  3. `make type`
  4. `make test`
- Add or update tests for:
  - domain constructor runtime constraint failures
  - service mapping correctness at boundaries
  - unchanged API response shape
  - unchanged eval artifact contract (`anchors.json` shape/version)

## Compatibility Requirements
- No breaking changes to:
  - API response contracts
  - persisted eval artifact schema versions
  - existing orchestrator/evaluator compatibility
- Any intentional contract/schema change must be versioned and documented before rollout.

## Done Criteria
1. Domain dataclass value objects exist for targeted primitives.
2. Runtime constraints are explicit and tested.
3. Boundary schemas remain authoritative and behavior-compatible.
4. Required checks pass for each rollout slice.
5. Relevant docs and tests are updated with each merged slice.
