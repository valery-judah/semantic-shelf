# Domain Modeling: Implementation Plan

## Goal
Implement the domain-modeling recommendations incrementally with minimal risk and clear validation gates.

## Rollout Plan
1. Create a types-only foundation PR.
- Add `src/books_rec_api/domain.py` with shared aliases:
  - `BookId`
  - `InternalUserId`
  - `ExternalIdpId`
  - `DatasetUserId`
  - `Score`
  - `AlgoId`
  - `RecsVersion`
  - `PopularityScope`
- Keep this PR behavior-neutral.

2. Apply aliases at the API/schema boundary.
- Update:
  - `src/books_rec_api/schemas/book.py`
  - `src/books_rec_api/schemas/user.py`
  - `src/books_rec_api/schemas/recommendation.py`
- Preserve existing `Field(...)` constraints and API response shape.

3. Complete the layering prerequisite in users flow.
- Refactor `src/books_rec_api/repositories/users_repository.py` to stop returning API schema objects directly.
- Move schema mapping to `src/books_rec_api/services/user_service.py`.
- Keep route behavior and payload contracts unchanged.

4. Type repository and service signatures.
- Update ID/scope parameters and return contracts in:
  - `src/books_rec_api/repositories/books_repository.py`
  - `src/books_rec_api/repositories/users_repository.py`
  - `src/books_rec_api/services/book_service.py`
  - `src/books_rec_api/services/user_service.py`
- Replace raw primitives with domain aliases where appropriate.

5. Migrate recommendation jobs.
- `scripts/job_compute_neighbors.py`:
  - Introduce `BookFeatures`, `NeighborScore`, `SimilarityRecord`.
  - Add metadata normalization for `authors`/`genres` (trim/drop empty).
- `scripts/job_compute_popularity.py`:
  - Type scope and payload contract.
  - Keep top-1000 + null-exclusion behavior explicit.

6. Validate each slice before merging.
- Run:
  1. `make fmt`
  2. `make lint`
  3. `make type`
  4. `make test`
- Require CI to enforce `make type`.

## Notes
- `NewType` and `TypedDict` improve static checking and readability; they do not provide runtime validation by themselves.
- Runtime data-quality rules (normalization/validation) must remain explicit in code paths that ingest or transform data.
