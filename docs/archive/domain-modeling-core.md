# Domain Modeling: System-Wide Application

## Overview
While our previous domain modeling efforts focused strictly on recommendation batch jobs, the API boundary and repository layers currently rely heavily on unstructured primitives (`str`, `float`, `dict`). Expanding the domain model system-wide allows the API schemas, repositories, and services to communicate using an explicit, shared ubiquitous language.

## Proposed Strategy

### 1. Centralize Domain Types
**Suggestion:** Create a central domain module `src/books_rec_api/domain.py` to hold shared value types, rather than defining them inside the batch job folder.
```python
from typing import Literal, NewType

BookId = NewType("BookId", str)
InternalUserId = NewType("InternalUserId", str)
ExternalIdpId = NewType("ExternalIdpId", str)
DatasetUserId = NewType("DatasetUserId", int)
Score = NewType("Score", float)
AlgoId = NewType("AlgoId", str)
RecsVersion = NewType("RecsVersion", str)
PopularityScope = Literal["global"]
```
**Reasoning:** If jobs use one definition of `BookId` and the API uses another (or relies on bare strings), we lose the benefits of type consistency. A single source of truth for semantic aliases improves static analysis coverage across the entire project. Distinguishing internal user IDs, external identity-provider IDs, and dataset user IDs prevents accidental mixing of different identity domains.

### 2. Update API Schemas (`src/books_rec_api/schemas/`)
**Suggestion:** Replace primitive types in Pydantic schemas with their corresponding Value Types.
- `schemas/book.py`: Use `BookId` for the `id` field.
- `schemas/user.py`: Use `InternalUserId` for `id` and `ExternalIdpId` for `external_idp_id`.
- `schemas/recommendation.py`: Use `BookId` for `book_id` and `similar_book_ids`, and `Score` for the recommendation score.

**Reasoning:** Pydantic supports `typing.NewType` natively. It continues to enforce runtime constraints (like `ge=0.0, le=1.0` on floats) and correctly generates OpenAPI specifications, while granting static type-checkers the ability to enforce strict type passing at the service boundary.

### 3. Fortify Repositories and Services
**Suggestion:** Update method signatures across `books_repository.py`, `users_repository.py`, and the service layer.
- Update `get_by_id(self, book_id: str)` to `get_by_id(self, book_id: BookId)`.
- Update `get_similarities(self, book_id: str)` to `get_similarities(self, book_id: BookId)`.
- Update `get_popularity(self, scope: str = "global")` to `get_popularity(self, scope: PopularityScope = "global")`.

**Reasoning:** The repository serves as the boundary between the strictly-typed domain and the loosely-typed database. Requiring Value Types at this boundary improves static type checking and readability in the service layer, reducing ambiguous string usage. This is a compile-time/static-analysis benefit; runtime validation still requires explicit checks where needed.

### 4. Database Models boundary
**Suggestion:** Keep SQLAlchemy models (`src/books_rec_api/models.py`) mapped to raw primitive types (`Mapped[str]`, `Mapped[float]`).
**Reasoning:** SQLAlchemy models are intrinsically tied to underlying database column types. While SQLAlchemy supports custom `TypeDecorator` objects, introducing them often complicates query building. Treating the repository layer as the conversion boundary provides the best balance of safety and ORM simplicity.

### 5. Layering Prerequisite (Users Flow)
**Suggestion:** Decouple repositories from API schema models before broad type rollout.
- Repositories should return ORM/domain records, not Pydantic API response models.
- Services should map repository/domain outputs to API schemas.

**Reasoning:** If repository methods directly return API schemas, the domain model cannot be cleanly enforced across boundaries. Separating persistence, domain/service logic, and transport schemas makes type aliases and records easier to apply consistently.

### 6. Runtime Validation Scope
**Suggestion:** Define explicit runtime validation rules for fields where correctness matters beyond static typing.
- Validate external identity headers as non-empty canonical strings.
- Normalize metadata collections (authors/genres) by trimming and dropping empty values.
- Keep timestamp handling consistently UTC and timezone-aware.

**Reasoning:** `NewType` and `TypedDict` improve static analysis but do not enforce runtime constraints by themselves. Runtime validation and normalization remain necessary for data quality and behavior consistency.

### 7. Strict Runtime & Persistence Boundary Enforcement
**Suggestion:** Enforce data shape boundaries dynamically to complement the static `NewType` bindings.
- **API Boundaries:** Upgrade domain primitives by wrapping `NewType` with `typing.Annotated` and Pydantic's `Field`. To satisfy both strict static type checkers (like Pyright, which rejects `Annotated` as the second argument to `NewType`) and Pydantic (which requires it for runtime validation), use the `typing.TYPE_CHECKING` idiom:
  ```python
  import typing
  from typing import Annotated
  from pydantic import Field
  
  if typing.TYPE_CHECKING:
      # Pyright sees a strict PEP-484 compliant type
      Score = typing.NewType("Score", float)
  else:
      # Pydantic sees runtime constraints via Annotated
      _ScoreFloat = Annotated[float, Field(ge=0.0, le=1.0)]
      Score = typing.NewType("Score", _ScoreFloat)
  ```
  This instructs Pydantic to apply strict constraints (ranges, regex patterns, min lengths) while deserializing HTTP requests, rejecting invalid inputs with a `422 Unprocessable Entity` immediately at the route edge, without breaking static analysis tools.
- **Service Boundaries:** Apply Pydantic's `@validate_call` decorator to core service methods (in `book_service.py` and `user_service.py`). This guarantees internal safety—if another internal Python module explicitly calls `get_book(book_id="")`, Pydantic generates a runtime `ValidationError`, preventing propagation of badly shaped internal data.
- **Persistence Boundaries:** Embed explicitly defined data quality expectations in `src/books_rec_api/models.py` via `CheckConstraint` (e.g., enforcing `users.id LIKE 'usr_%'` or ensuring `book_popularity.scope IN ('global')`). This serves as the ultimate fallback constraint in case a malicious or erroneous manual database script bypasses the application logic entirely.

**Reasoning:** While static types (`mypy`) prove mathematical correctness at compile-time, an external REST API and PostgreSQL database are dynamic environments. Bridging static aliases (`NewType`) with runtime evaluators (`Annotated`, `CheckConstraint`, `@validate_call`) creates an airtight domain model where illegal states are entirely unrepresentable across all IO boundaries.

## Implementation Plan
1. Create `src/books_rec_api/domain.py` with shared Value Types.
2. Update Pydantic schemas (`book.py`, `user.py`, `recommendation.py`).
3. Update Repository and Service method signatures.
4. Refactor repositories to avoid returning API schema objects directly (especially in users flow), then apply domain types at repository/service boundaries.
5. Update the Batch Jobs (`job_compute_neighbors.py`, `job_compute_popularity.py`) to import from the new domain module instead of defining types inline.
6. Add/adjust runtime validation and normalization where static typing is insufficient.
7. Run the repository quality gate (`make fmt`, `make lint`, `make type`, `make test`) to ensure systemic type coherence.
