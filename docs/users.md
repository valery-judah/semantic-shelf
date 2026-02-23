# query

Let's design a module and its structure for `users` in this books recommendation system repo. The repo is a Python monolith with FastAPI and Pydantic (you can propose other libraries, but must stay compatible with current project constraints).

## Domain Modeling: User

When security, authentication, and identity management are offloaded to an external specialized service (Identity Provider or IdP), the internal system only needs a "shadow" (or "stub") user record. This record acts as the anchor for domain-specific relational data (interactions, shelves, preferences) without bearing credential storage liabilities.

Pattern: decoupling security from business processes.

```json
{
  "internal_user_id": "usr_01H9X...",
  "domain_preferences": {
    "preferred_genres": ["scifi", "hard_sf"],
    "ui_theme": "dark"
  }
}
```

## User Module Design

The shadow user pattern is effective for isolating recommendation-domain logic from identity-management complexity. By offloading authentication to an external IdP, the internal `users` module remains a boundary for user-specific state and relations inside this API.

This document keeps the original system-level design depth but corrects it for the **current repository state**:
- package root is `src/books_rec_api/` (not `src/modules/...`);
- current app exposes `GET /me/recommendations`;
- no DB session dependency or auth verification exists yet;
- repository/service layers are present but minimal.

### Assumptions and Constraints

- **Database (target state)**: PostgreSQL is a good fit. `JSONB` is appropriate for `domain_preferences` where selective querying/indexing is useful.
- **ORM and Validation (target state)**: SQLAlchemy 2.0 + Pydantic v2.
- **Primary Keys**: ULID is a valid choice over UUID for index locality.
- **Provisioning Strategy**: Just-In-Time (JIT) provisioning of internal users on first valid external identity.
- **Security Boundary**: This service should not expose `/register` or `/login`; it should consume trusted identity context.

Critique:
- These assumptions are sound for a production direction, but they are ahead of current MVP. Implementing all of them immediately will create infrastructure work that is not required to ship user-facing behavior.

### Module Directory Structure

Original proposal used a domain module tree under `src/modules/users`. In this repo, align with existing structure:

```text
src/books_rec_api/
├── api/
│   └── routes/
│       └── users.py
├── schemas/
│   └── user.py
├── services/
│   └── user_service.py
├── repositories/
│   └── users_repository.py
└── dependencies/
    └── auth.py   # optional; can also live beside routes initially
```

Critique:
- Extraction-ready domain folders are valuable later, but forcing a new top-level module pattern now would be inconsistent with this codebase and increase churn.

### Data Models (`models.py`) - Target SQLAlchemy Shape

If/when persistence is added, the model can follow:

```python
from datetime import datetime, timezone
from sqlalchemy import String, text, Index, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from books_rec_api.db.base import Base  # placeholder path for future DB layer


class User(Base):
    __tablename__ = "users"

    # internal_user_id (ULID, e.g., 01H9X...)
    id: Mapped[str] = mapped_column(String(26), primary_key=True)

    # External subject claim from IdP token
    external_idp_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)

    # Domain-specific preferences
    domain_preferences: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("ix_users_external_idp_id", "external_idp_id"),
    )
```

Corrections vs original:
- Repo path is `books_rec_api...`, not `src.core...` / `src.modules...`.
- Prefer timezone-aware datetimes instead of naive `datetime.utcnow()`.

Critique:
- Declaring this now in docs is fine, but implementation should be deferred until a DB base/session is introduced in this repo.

### Domain Schemas (`schemas/user.py`)

Pydantic v2 models should provide explicit contracts.

```python
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class DomainPreferences(BaseModel):
    preferred_genres: list[str] = Field(default_factory=list)
    ui_theme: str = "dark"
    # future examples: author_blocklist: list[str], max_book_length: int | None


class UserBase(BaseModel):
    domain_preferences: DomainPreferences = Field(default_factory=DomainPreferences)


class UserRead(UserBase):
    id: str
    external_idp_id: str
    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    # partial update payload
    domain_preferences: Optional[DomainPreferences] = None
```

Correction:
- Original alias mapping `internal_user_id: str = Field(alias="id")` is workable, but usually unnecessary complexity unless external API strictly requires different key names.

Critique:
- `UserUpdate` with nested full object can over-constrain partial updates. Consider a dedicated partial preferences model if you need patch semantics per field.

### Business Logic and JIT Provisioning (`services/user_service.py`)

Service-layer intent from original remains valid.

```python
import ulid

from books_rec_api.schemas.user import UserRead, DomainPreferences
from books_rec_api.repositories.users_repository import UsersRepository


class UserService:
    def __init__(self, repo: UsersRepository) -> None:
        self.repo = repo

    async def get_or_create_shadow_user(self, external_idp_id: str) -> UserRead:
        user = await self.repo.get_by_external_id(external_idp_id)
        if user is None:
            user = await self.repo.create(
                id=f"usr_{ulid.new().str}",
                external_idp_id=external_idp_id,
                domain_preferences=DomainPreferences().model_dump(),
            )
        return user

    async def update_preferences(self, user_id: str, preferences: dict) -> UserRead:
        return await self.repo.update_preferences(user_id, preferences)
```

Corrections:
- Inject repository into service to keep testing simple.
- Use repo paths aligned with current package.

Critique:
- Introducing `ulid` adds a new dependency; UUIDv7 (stdlib soon) or UUID4 may be sufficient at MVP. Keep ULID if sorting/index locality is a clear requirement.

### API Router and Dependency Injection (`api/routes/users.py` + auth dependency)

Original dependency chain is still the right boundary, but references to `src.core.auth` and `get_db_session` are not available in this repo yet.

Target API shape:

```python
from fastapi import APIRouter, Depends, HTTPException, status

from books_rec_api.schemas.user import UserRead, UserUpdate
from books_rec_api.services.user_service import UserService
from books_rec_api.dependencies.auth import get_external_idp_id
from books_rec_api.dependencies.users import get_user_service

router = APIRouter(tags=["users"])


@router.get("/me", response_model=UserRead)
async def get_my_profile(
    external_idp_id: str = Depends(get_external_idp_id),
    svc: UserService = Depends(get_user_service),
) -> UserRead:
    return await svc.get_or_create_shadow_user(external_idp_id)


@router.patch("/me/preferences", response_model=UserRead)
async def update_my_preferences(
    payload: UserUpdate,
    external_idp_id: str = Depends(get_external_idp_id),
    svc: UserService = Depends(get_user_service),
) -> UserRead:
    user = await svc.get_or_create_shadow_user(external_idp_id)
    if payload.domain_preferences is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="domain_preferences is required",
        )
    return await svc.update_preferences(
        user_id=user.id,
        preferences=payload.domain_preferences.model_dump(exclude_unset=True),
    )
```

Corrections:
- Remove `prefix="/users"` from original if you want consistency with existing `/me/recommendations` style. Keep `/me` and `/me/preferences` at root scope.

Critique:
- If route namespace collisions become a concern, using `/users/me` is cleaner. For now, keeping `/me/...` matches the current API style.

## Repository Layer

Original concern about read-modify-write races is correct for a SQL backend. The JSONB merge approach is strong when persistence exists.

### Assumptions and Constraints

- **Concurrency**: preference updates should be atomic.
- **Top-Level Merging**: JSONB `||` does shallow merge only.
- **Transaction Management**: repository can `flush`, commit handled per-request at higher layer.

Critique:
- The MVP currently has no database/session management. Implement an in-memory repository first with the same interface, then swap internals to SQLAlchemy later.

### Data Access Layer (`repositories/users_repository.py`) - SQL Target

```python
from typing import Any
from sqlalchemy import cast, select, update
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from books_rec_api.models.user import User


class UsersRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_external_id(self, external_idp_id: str) -> User | None:
        stmt = select(User).where(User.external_idp_id == external_idp_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        id: str,
        external_idp_id: str,
        domain_preferences: dict[str, Any],
    ) -> User:
        new_user = User(
            id=id,
            external_idp_id=external_idp_id,
            domain_preferences=domain_preferences,
        )
        self.session.add(new_user)
        await self.session.flush()
        return new_user

    async def update_preferences(
        self,
        user_id: str,
        partial_preferences: dict[str, Any],
    ) -> User | None:
        if not partial_preferences:
            stmt = select(User).where(User.id == user_id)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()

        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(
                domain_preferences=User.domain_preferences.op("||")(
                    cast(partial_preferences, JSONB)
                )
            )
            .returning(User)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.scalar_one_or_none()
```

Corrections:
- Type hints modernized (`User | None`).
- Package paths aligned with this repo.

Critique:
- JSONB merge semantics need tests for list replacement behavior; it does not append list items by default.

## Why This Approach Scales

1. **Network Efficiency**: send only diffs, not full preference blobs.
2. **Safety**: DB-side atomic update reduces lost updates compared to naive read-modify-write.
3. **Modularity**: service/repository boundaries allow migrating from in-memory MVP to Postgres with minimal API-surface change.

## Practical Phasing for This Repository

1. Implement `schemas/user.py` and an in-memory `repositories/users_repository.py`.
2. Implement `services/user_service.py` with JIT create.
3. Add `/me` and `/me/preferences` routes.
4. Add dependency that returns a stable development `external_idp_id`.
5. Integrate user context into `/me/recommendations`.
6. Add SQLAlchemy + Postgres layer later without changing route contracts.

## Tests (Required)

Add `tests/test_users_api.py`:
- `GET /me` returns user profile and default preferences.
- first request creates user (JIT).
- repeated requests for same external ID return same internal ID.
- `PATCH /me/preferences` updates only provided fields.
- invalid payload returns 422 or 400 (based on contract choice).

Update recommendation tests:
- `tests/test_recommendations_api.py` should continue passing with user-resolution dependency in place.

## Definition of Done

1. Users module design is aligned with `src/books_rec_api` layout.
2. No auth credential logic is introduced in this service.
3. API contracts are explicit via Pydantic models.
4. Concurrency and persistence assumptions are documented (not hidden).
5. Design remains implementation-ready for both in-memory MVP and future Postgres.
