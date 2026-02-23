# Users Module Design (Repo-Aligned v0)

## Goal
Define a `users` module for this repository that supports domain-level user state for recommendations, while keeping authentication and credentials outside this service.

## Current Repository Reality
- FastAPI app with one route: `GET /me/recommendations`.
- Source layout: `src/books_rec_api/...`.
- Recommendation logic is currently a stub in `services/recommendation_service.py`.
- No persistence layer implementation yet (`repositories/books_repository.py` is a placeholder).
- No authentication dependency or identity mapping yet.

This design keeps those constraints in mind and proposes an incremental path.

## Domain Model: Shadow User
When identity is handled by an external IdP, this API stores only an internal user record used for recommendation-domain relations and preferences.

Example shape:

```json
{
  "id": "usr_01H9X...",
  "external_idp_id": "auth0|abc123",
  "domain_preferences": {
    "preferred_genres": ["scifi", "hard_sf"],
    "ui_theme": "dark"
  }
}
```

## Proposed Module Structure

```text
src/books_rec_api/
  api/
    routes/
      users.py
  schemas/
    user.py
  services/
    user_service.py
  repositories/
    users_repository.py
```

Notes:
- This mirrors existing repo conventions (`api/routes`, `schemas`, `services`, `repositories`).
- Keep implementation minimal and testable first; avoid premature infra complexity.

## API Surface (v0)
- `GET /me`
  - Returns current shadow user profile.
- `PATCH /me/preferences`
  - Updates `domain_preferences` fields used by recommendation logic.

No `/register` or `/login` routes should be added here.

## Schemas (`src/books_rec_api/schemas/user.py`)
- `DomainPreferences`
  - `preferred_genres: list[str] = []`
  - `ui_theme: str = "dark"`
- `User`
  - `id: str`
  - `external_idp_id: str`
  - `domain_preferences: DomainPreferences`
- `UserPreferencesUpdate`
  - Partial update payload for preference fields.

Keep response models explicit (no untyped dict responses).

## Repository Plan (`src/books_rec_api/repositories/users_repository.py`)
Given the current MVP, start with an in-memory repository abstraction that can be replaced later.

Required methods:
- `get_by_external_id(external_idp_id: str) -> User | None`
- `get_by_id(user_id: str) -> User | None`
- `create(user: User) -> User`
- `update_preferences(user_id: str, partial: UserPreferencesUpdate) -> User | None`

Later, this can move to PostgreSQL without changing the service contract.

## Service Layer (`src/books_rec_api/services/user_service.py`)
Core behavior:
- `get_or_create_shadow_user(external_idp_id: str) -> User`
  - Lookup by external subject.
  - If not found, create `id` (e.g., `usr_<ulid_or_uuid>`) with default preferences.
- `update_preferences(user_id: str, partial: UserPreferencesUpdate) -> User`

This service becomes the integration point for recommendation personalization.

## Auth and Identity Boundary
For this repo stage:
- Add a temporary dependency that resolves a stable external user ID for local/dev usage.
- Keep it swappable for real JWT verification later.

Suggested dependency contract:
- Input: request context/token
- Output: `external_idp_id: str`

`users` logic should depend only on this contract, not on IdP-specific SDK code.

## Recommendations Integration
Current endpoint is `GET /me/recommendations`. To align with per-user recommendations:
- Resolve current shadow user first.
- Feed `domain_preferences` (and later interaction history) into ranking.
- Keep response schema in `schemas/recommendation.py` unchanged unless product requirements change.

## Tests to Add
Create `tests/test_users_api.py`:
- `GET /me` returns user shape and default preferences.
- first request provisions user (JIT behavior).
- `PATCH /me/preferences` updates only provided fields.
- invalid payloads return 422.

Update recommendation tests as needed:
- Ensure `GET /me/recommendations` still works with user resolution path.

## Incremental Delivery Plan
1. Add user schemas and in-memory users repository.
2. Add user service with get-or-create behavior.
3. Add `users` routes and include router in `main.py`.
4. Add tests for users endpoints.
5. Integrate user context into recommendation service.
6. Replace in-memory storage with real persistence when data layer is introduced.

## Non-Goals (v0)
- Credential storage.
- IdP token issuance or login UX.
- Full RBAC/permissions model.
- Complex preference query indexing.

## Definition of Done For Users v0
- `/me` and `/me/preferences` implemented with explicit Pydantic models.
- User behavior covered by tests.
- Existing recommendation endpoint remains passing.
- Docs updated (`docs/users.md`, and `docs/reqs-v0.md` if API contract changes).
