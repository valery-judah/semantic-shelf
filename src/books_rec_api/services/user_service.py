from uuid import uuid4

from books_rec_api.repositories.users_repository import UsersRepository
from books_rec_api.schemas.user import DomainPreferences, DomainPreferencesUpdate, UserRead


class UserService:
    def __init__(self, repo: UsersRepository) -> None:
        self.repo = repo

    def get_or_create_shadow_user(self, external_idp_id: str) -> UserRead:
        existing = self.repo.get_by_external_id(external_idp_id)
        if existing is not None:
            return existing

        user_id = f"usr_{uuid4()}"
        return self.repo.create(
            id=user_id,
            external_idp_id=external_idp_id,
            domain_preferences=DomainPreferences(),
        )

    def update_preferences(self, user_id: str, patch: DomainPreferencesUpdate) -> UserRead | None:
        return self.repo.update_preferences(user_id=user_id, patch=patch)
