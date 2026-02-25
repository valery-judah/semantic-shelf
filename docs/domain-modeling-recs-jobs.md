# Domain Modeling: Recommendation Jobs (`job_compute_neighbors.py` + `job_compute_popularity.py`)

## Purpose
Define job-specific domain modeling guidance for recommendation batch jobs while reusing system-wide conventions from the core domain model plan.

Covered jobs:
- `scripts/job_compute_neighbors.py`
- `scripts/job_compute_popularity.py`

## Dependency
This document depends on:
- [docs/domain-modeling-core.md](/Users/val/ml/projects/books-rec/semantic-shelf/docs/domain-modeling-core.md)

Shared value types and identity aliases are defined centrally in `src/books_rec_api/domain.py` and must be imported by job scripts rather than redefined locally.

## Job-Shared Guidance

### 1. Use Core Domain Types (Do Not Redefine)
Import shared aliases from `src/books_rec_api/domain.py` (for example, `BookId`, `Score`, `RecsVersion`, `AlgoId`, `PopularityScope`).

### 2. Runtime Conventions in Job Scripts
- Use UTC timestamps consistently and keep `recs_version` format stable (`%Y-%m-%dT%H:%M:%SZ`).
- Use explicit constants for stable identifiers (algorithm id and popularity scope).
- Normalize metadata collections (`authors`, `genres`) by trimming and dropping empty values before scoring.

### 3. Record and Payload Discipline
- In-memory compute structures: `@dataclass(slots=True, frozen=True)` or `NamedTuple`.
- DB write payload dicts: `TypedDict`.

## Boundaries
- `NewType`/`TypedDict` provide static analysis and readability benefits, not runtime validation by themselves.
- Runtime normalization and validation remain explicit job logic.
- SQLAlchemy ORM models remain primitive-typed; conversion boundaries live above ORM definitions.

## Appendix A: Neighbors Job (`job_compute_neighbors.py`)

### A1. Domain Records
```python
from datetime import datetime
from dataclasses import dataclass
from typing import NamedTuple, TypedDict

@dataclass(frozen=True, slots=True)
class BookFeatures:
    authors: frozenset[str]
    genres: frozenset[str]

class NeighborScore(NamedTuple):
    book_id: BookId
    score: Score

class SimilarityRecord(TypedDict):
    book_id: BookId
    neighbor_ids: list[BookId]
    recs_version: RecsVersion
    algo_id: AlgoId
    updated_at: datetime
```

### A2. Performance Constraint
The pairwise comparison is `O(N^2)`, so keep score records lightweight and avoid per-iteration heavy allocations.

### A3. Behavioral Checks
- Exclude self-neighbor matches.
- Keep deterministic score ordering (descending score).
- Confirm top-`k` truncation behavior and tie-handling expectations in tests.

## Appendix B: Popularity Job (`job_compute_popularity.py`)

### B1. Domain Records / Contracts
Even with ORM object writes, model the input selection and output contract explicitly.

Optional typed payload shape:
```python
from datetime import datetime
from typing import TypedDict

class PopularityRecord(TypedDict):
    scope: PopularityScope
    book_ids: list[BookId]
    recs_version: RecsVersion
    updated_at: datetime
```

### B2. Selection Contract
Define and document the contract for "popular":
- ordered by `ratings_count` descending
- null ratings excluded
- capped to top 1000

### B3. Single-Row Scope Semantics
Current behavior deletes old `global` scope row(s) and inserts a fresh row.
Validate this as intentional and test:
- empty dataset behavior
- id list size cap
- version/timestamp update per run

## Implementation Sequence
1. Complete core rollout in [docs/domain-modeling-core.md](/Users/val/ml/projects/books-rec/semantic-shelf/docs/domain-modeling-core.md) (shared domain module and boundary typing strategy).
2. Migrate `job_compute_neighbors.py` to import core aliases and apply neighbors-specific records.
3. Migrate `job_compute_popularity.py` to import core aliases and apply popularity-specific contracts.
4. Add/update tests to cover job contracts and edge cases.
5. Run quality gate: `make fmt`, `make lint`, `make type`, `make test`.
6. Ensure CI enforces `make type` for ongoing static-check coverage.

## Verification Matrix
### `job_compute_neighbors.py`
- anchor book is not returned in neighbors
- duplicates are removed while preserving ordering intent
- top-`k` truncation is respected
- ordering is deterministic for equal-score conditions per defined tie policy

### `job_compute_popularity.py`
- ordering by `ratings_count` descending
- null `ratings_count` excluded
- capped to top 1000
- `global` scope row replacement semantics hold on reruns
