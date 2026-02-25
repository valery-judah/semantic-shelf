# Domain Modeling: Recommendation Jobs (`job_compute_neighbors.py` + `job_compute_popularity.py`)

## Purpose
Create a single refactoring plan for recommendation batch jobs so type names, data-shape contracts, and runtime conventions stay consistent across scripts.

Covered jobs:
- `scripts/job_compute_neighbors.py`
- `scripts/job_compute_popularity.py`

## Common Plan (Shared Across Jobs)

### 1. Shared Value Types
Define semantic aliases with `typing.NewType` (or `type` aliases where clearer) in a shared module.

Suggested baseline:
```python
from datetime import datetime
from typing import NewType, Literal

BookId = NewType("BookId", str)
Score = NewType("Score", float)
RecsVersion = NewType("RecsVersion", str)
AlgoId = NewType("AlgoId", str)
PopularityScope = Literal["global"]
Timestamp = datetime
```

Notes:
- `NewType` is for static typing and readability, not runtime enforcement.
- Keep `PopularityScope` explicit so `"global"` is not repeated as an untyped string literal.

### 2. Shared Runtime Conventions
- Use one UTC timestamp source per run where possible.
- Keep `recs_version` format consistent (`%Y-%m-%dT%H:%M:%SZ`).
- Use explicit constants for stable identifiers:
  - neighbors algorithm id (for example, `meta_v0`)
  - popularity scope (`global`)

### 3. Shared Record and Payload Discipline
Use structured records at in-memory boundaries and typed dict payloads at DB write boundaries.

Guideline:
- In-memory compute structures: `@dataclass(slots=True, frozen=True)` or `NamedTuple`.
- DB insert/update dicts: `TypedDict`.

### 4. Shared Data Hygiene
Normalize metadata before scoring or persisting:
- trim whitespace
- drop empty values
- deduplicate via sets/frozensets

This remains runtime logic; typing annotations do not replace it.

### 5. Shared Quality Gate
For refactors in either job, run:
1. `make fmt`
2. `make lint`
3. `make type`
4. `make test`

Also enforce `make type` in CI so static guarantees are continuously checked.

## Appendix A: Neighbors Job (`job_compute_neighbors.py`)

### A1. Domain Records
```python
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
    updated_at: Timestamp
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
from typing import TypedDict

class PopularityRecord(TypedDict):
    scope: PopularityScope
    book_ids: list[BookId]
    recs_version: RecsVersion
    updated_at: Timestamp
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
1. Add shared domain typing module for recommendation jobs.
2. Migrate neighbors job records and payload typing.
3. Migrate popularity job constants and payload typing.
4. Add/update tests to cover contracts in both jobs.
5. Run the quality gate (`fmt`, `lint`, `type`, `test`).
