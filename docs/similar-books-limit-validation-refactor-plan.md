# Similar Books `limit` Validation Refactor Plan

## Why We Should Refactor

The current `GET /v1/books/{book_id}/similar` route declares:

- `limit: int = Query(20, ge=0, le=100, ...)`

FastAPI enforces `ge`/`le` before our handler and returns `422 Unprocessable Entity` for out-of-range values.  
Our feature contract in [`docs/similar-books.md`](/Users/val/ml/projects/books-rec/semantic-shelf/docs/similar-books.md) specifies:

- invalid `limit` should return `400 Bad Request`

This mismatch is a client-facing API contract break. Clients built to treat invalid `limit` as `400` may mis-handle errors when they receive `422`.

## What We Should Refactor

### 1. Move Range Validation from FastAPI Param Constraints to Explicit Route Logic

In [`src/books_rec_api/api/routes/books.py`](/Users/val/ml/projects/books-rec/semantic-shelf/src/books_rec_api/api/routes/books.py):

- Remove `ge=0` and `le=100` from the `limit` query declaration.
- Keep `limit` as an integer query param with default `20`.
- Add explicit guard in `get_similar_books`:
  - if `limit < 0` or `limit > 100`, raise:
    - `HTTPException(status_code=400, detail="...")`

Note: non-integer query values should still be handled by framework parsing (422), unless we choose to broaden contract behavior later.

### 2. Update API Tests to Enforce Contract

Add/adjust route tests to assert:

- `limit=-1` returns `400`
- `limit=101` returns `400`
- valid bounds (`0`, `100`) still return success path behavior

If existing tests currently expect `422`, update them to `400` for out-of-range numeric values.

### 3. Regenerate API Spec Artifact

The committed artifact [`docs/openapi.json`](/Users/val/ml/projects/books-rec/semantic-shelf/docs/openapi.json) currently advertises `422` for validation failures from schema constraints.  
After refactor, regenerate this file and confirm response documentation aligns with actual behavior for invalid numeric ranges.

## Scope and Non-Goals

In scope:

- Out-of-range numeric `limit` handling (`< 0`, `> 100`) returns `400`.

Out of scope:

- Changing behavior for non-integer `limit` parsing errors.
- Broader global exception-mapping changes across unrelated endpoints.

## Acceptance Criteria

1. `GET /v1/books/{book_id}/similar?limit=-1` returns `400`.
2. `GET /v1/books/{book_id}/similar?limit=101` returns `400`.
3. Existing success behavior remains unchanged for valid limits.
4. Tests cover both invalid range cases.
5. Docs/spec reflect the contract (`400` for invalid numeric range).
