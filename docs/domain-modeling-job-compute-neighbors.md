# Domain Modeling: `job_compute_neighbors.py`

## Overview
The `scripts/job_compute_neighbors.py` script currently relies on Python's built-in primitive types (`str`, `float`, `int`) and unstructured collections (like raw `dict`s and `tuple`s) for moving data around. By applying domain modeling concepts—specifically **value types** and **records**—we can make the ubiquitous language of the domain explicit, improve type safety, and enhance overall code readability.

## Suggestions and Reasoning

### 1. Value Types for Domain Concepts
**Suggestion:** Use `typing.NewType` to create semantic types like `BookId` and `Score`.
**Reasoning:** Throughout the script, `str` is used for book IDs and `float` is used for similarity scores. Defining `BookId = NewType("BookId", str)` and `Score = NewType("Score", float)` makes the code self-documenting. It improves static type-checking and readability by signaling to type-checkers (like mypy or pyright) that functions explicitly expect a `BookId` rather than any arbitrary string, though at runtime they remain standard strings and floats.

### 2. `BookFeatures` Record
**Suggestion:** Replace the loose dictionary `{"authors": set(), "genres": set()}` with a frozen `@dataclass` (or `NamedTuple`) utilizing `frozenset`.
```python
@dataclass(frozen=True, slots=True)
class BookFeatures:
    authors: frozenset[str]
    genres: frozenset[str]
```
**Reasoning:** Dictionaries are inherently mutable and loosely typed. A dataclass explicitly guarantees field structure (that a book feature object has exactly `authors` and `genres` attributes), enforcing structure and enabling better IDE autocomplete. By using `frozenset` along with `frozen=True` and `slots=True`, we ensure true immutability and memory efficiency, preventing accidental mutations of the underlying collections.

### 3. `NeighborScore` Record
**Suggestion:** Replace the generic `(candidate_id, score)` tuple with a `@dataclass` or `NamedTuple` to represent pairwise similarity scoring.
```python
class NeighborScore(NamedTuple):
    book_id: BookId
    score: Score
```
**Reasoning:** Raw tuples like `(str, float)` obfuscate what the values represent, forcing developers to look up the tuple creation to understand index `0` and index `1`. A `NamedTuple` named `NeighborScore` explicitly models the relationship (a book and its similarity score) while remaining performant in the $O(N^2)$ tight loops.

### 4. `SimilarityRecord` Type
**Suggestion:** Use a `TypedDict` for the dictionaries that are appended to the `similarities_to_insert` list.
```python
class SimilarityRecord(TypedDict):
    book_id: BookId
    neighbor_ids: list[BookId]
    recs_version: str
    algo_id: str
    updated_at: datetime
```
**Reasoning:** The SQLAlchemy bulk insert natively accepts a list of dictionaries (`session.execute(insert(BookSimilarity).values(batch))`). A `TypedDict` catches schema-shape issues during static analysis (via tools like mypy/pyright), ensuring that every record appended to the batch matches the expected database schema before the code is even run, while adding zero overhead at runtime.

## Technical Considerations
- **Performance Overhead:** The similarity calculation loop is $O(N^2)$, so introducing heavy objects could drastically slow it down. Utilizing lightweight constructs like `NamedTuple` and `@dataclass(slots=True)` minimizes this memory footprint and execution overhead.
- **SQLAlchemy Compatibility:** By defining `SimilarityRecord` as a `TypedDict`, we achieve static type checking without modifying the runtime behavior—it remains a standard Python `dict` compatible with SQLAlchemy's `insert().values()`.
- **Runtime Data Hygiene:** `authors` and `genres` should still be normalized/validated at load time (for example, trimming whitespace and dropping empty strings) because type annotations do not enforce value quality.

## Non-Goals and Boundaries
- `NewType` and `TypedDict` improve static analysis, readability, and refactor safety, but they do not perform runtime validation by themselves.
- Value-level constraints (like rejecting malformed author names or empty genre entries) still require explicit runtime checks.

## Implementation Checklist
1. Introduce `BookId` and `Score` (`typing.NewType`) where IDs and scores are passed between functions.
2. Replace the raw feature dictionaries with a `BookFeatures` record using `frozenset[str]`.
3. Replace `(candidate_id, score)` tuples with a `NeighborScore` record.
4. Type `similarities_to_insert` entries with `SimilarityRecord` (`TypedDict`).
5. Add/adjust normalization logic for metadata (`authors` and `genres`) during data loading.
6. Run `make type` and `make test` locally.
7. Ensure CI includes `make type` so static guarantees described here are continuously enforced.
