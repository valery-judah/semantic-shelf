# Users Module v0 Implementation Plan (Users + Recommendations Wiring)

## Summary
Implement a production-shaped but MVP-light `users` module in `src/books_rec_api` using in-memory storage, header-based dev identity, and deterministic contracts. Add `/me` and `/me/preferences`, wire `/me/recommendations` through current-user resolution, and keep recommendation response schema unchanged. Use `UUID4`-based internal IDs with `usr_` prefix and top-level merge semantics for preference updates.

## Decisions Locked
- Scope: implement users endpoints and wire user context into recommendations.
- Identity source (v0): required header-based dependency (`X-User-Id`).
- Internal ID format: `usr_<uuid4>`.
- PATCH behavior: top-level merge of `domain_preferences`.

## Public API / Interface Changes
1. New endpoint: `GET /me`
   - Response model: user profile with `id`, `external_idp_id`, `domain_preferences`.
   - Behavior: JIT create user on first request for a given `X-User-Id`.
2. New endpoint: `PATCH /me/preferences`
   - Request model: partial `domain_preferences` fields.
   - Response model: updated user profile.
   - Behavior: top-level merge into existing preferences.
3. Existing endpoint behavior change: `GET /me/recommendations`
   - Still returns current `RecommendationsResponse`.
   - Internally resolves current user via same identity dependency; no response contract change.

## Files To Add
1. `src/books_rec_api/schemas/user.py`
   - `DomainPreferences`
   - `DomainPreferencesUpdate` (all-optional fields for patch semantics)
   - `UserRead`
   - `UserPreferencesPatchRequest` (wrapper with `domain_preferences`)
2. `src/books_rec_api/repositories/users_repository.py`
   - In-memory repository, keyed by `id` and `external_idp_id`.
   - Methods: `get_by_external_id`, `get_by_id`, `create`, `update_preferences`.
3. `src/books_rec_api/services/user_service.py`
   - `get_or_create_shadow_user(external_idp_id: str) -> UserRead`
   - `update_preferences(user_id: str, patch: DomainPreferencesUpdate) -> UserRead`
4. `src/books_rec_api/dependencies/auth.py`
   - `get_external_idp_id(request: Request) -> str` from `X-User-Id`.
   - Return `401` if missing/blank.
5. `src/books_rec_api/dependencies/users.py`
   - App-level singleton repo provider.
   - `get_users_repository()`
   - `get_user_service()`
6. `src/books_rec_api/api/routes/users.py`
   - `GET /me`
   - `PATCH /me/preferences`

## Files To Modify
1. `src/books_rec_api/main.py`
   - Include new users router.
2. `src/books_rec_api/api/routes/recommendations.py`
   - Add dependency for identity + user service.
   - Ensure user is resolved/created before recommendations are returned.
3. `src/books_rec_api/services/recommendation_service.py`
   - Accept user context parameter (for now may be unused in ranking logic).
   - Keep output identical to current contract.
4. `src/books_rec_api/schemas/__init__.py`
   - Export new user schemas if package exports are maintained.
5. `src/books_rec_api/services/__init__.py` and `src/books_rec_api/repositories/__init__.py`
   - Export new service/repository classes if this repo uses explicit exports.
6. `docs/reqs-v0.md`
   - Add users endpoints and note `X-User-Id` requirement for MVP auth boundary.

## Data Contracts (Exact v0)
1. `DomainPreferences`
   - `preferred_genres: list[str]` default `[]`
   - `ui_theme: str` default `"dark"`
2. `DomainPreferencesUpdate`
   - `preferred_genres: list[str] | None = None`
   - `ui_theme: str | None = None`
3. `UserRead`
   - `id: str`
   - `external_idp_id: str`
   - `domain_preferences: DomainPreferences`
4. `UserPreferencesPatchRequest`
   - `domain_preferences: DomainPreferencesUpdate`

## Endpoint Behavior Details
1. `GET /me`
   - Requires `X-User-Id`.
   - If external ID unseen: create user with default preferences.
   - If seen: return existing user.
2. `PATCH /me/preferences`
   - Requires `X-User-Id`.
   - Requires body `domain_preferences`.
   - Merge only provided fields (`None` means omitted, not overwrite).
   - Return updated full user state.
3. `GET /me/recommendations`
   - Requires `X-User-Id`.
   - Resolves user first, then returns recommendations list.

## Error Contract
1. Missing or empty `X-User-Id`: `401` with explicit detail message.
2. Invalid request body shape/types: `422` (FastAPI validation).
3. Empty patch object behavior:
   - If `domain_preferences` exists but has no fields set, return current user unchanged (`200`).

## Test Plan
1. Add `tests/test_users_api.py`
   - `GET /me` creates and returns default profile.
   - Repeated `GET /me` with same header returns same `id`.
   - Different `X-User-Id` values create distinct users.
   - `PATCH /me/preferences` updates only provided keys.
   - `PATCH /me/preferences` with partial payload preserves omitted fields.
   - Missing `X-User-Id` returns `401`.
   - Invalid preference type returns `422`.
2. Update `tests/test_recommendations_api.py`
   - Include `X-User-Id` header in request.
   - Preserve existing assertions for recommendation payload shape/content.
3. Regression checks
   - All existing tests remain green.
   - Recommendation response schema unchanged.

## Implementation Sequence
1. Create schema models.
2. Implement in-memory users repository.
3. Implement users service with JIT creation and merge update.
4. Implement auth and service dependencies.
5. Add users routes.
6. Wire users router in app.
7. Update recommendations route/service to resolve user context.
8. Add/update tests.
9. Update docs.
10. Run quality gate: `make fmt`, `make lint`, `make type`, `make test`.

## Acceptance Criteria
1. `/me` and `/me/preferences` are available and tested.
2. `/me/recommendations` still passes previous response expectations.
3. Identity is consistently derived from `X-User-Id`.
4. Patch merge behavior is deterministic and covered by tests.
5. No DB/auth provider integration is required for v0.
6. Docs reflect current API contracts and v0 auth mechanism.

## Assumptions and Defaults
- Persistence remains in-memory for this phase.
- App process lifetime defines data lifetime.
- Concurrency requirements are minimal for MVP; no cross-process consistency guarantee yet.
- Future migration path to SQLAlchemy/Postgres is preserved by service/repository boundaries.
