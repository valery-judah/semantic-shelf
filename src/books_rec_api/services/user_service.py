from uuid import uuid4

from pydantic import validate_call

from books_rec_api.domain import ExternalIdpId, InternalUserId
from books_rec_api.models import User as UserModel
from books_rec_api.repositories.users_repository import UsersRepository
from books_rec_api.schemas.user import DomainPreferences, DomainPreferencesUpdate, UserRead


class UserService:
    def __init__(self, repo: UsersRepository) -> None:
        self.repo = repo

    def _map_to_schema(self, user_model: UserModel) -> UserRead:
        return UserRead(
            id=InternalUserId(user_model.id),
            external_idp_id=ExternalIdpId(user_model.external_idp_id),
            domain_preferences=DomainPreferences(**user_model.domain_preferences),
        )

    @validate_call
    def get_or_create_shadow_user(self, external_idp_id: ExternalIdpId) -> UserRead:
        existing = self.repo.get_by_external_id(external_idp_id)
        if existing is not None:
            return self._map_to_schema(existing)

        user_id = InternalUserId(f"usr_{uuid4()}")
        new_user = self.repo.create(
            id=user_id,
            external_idp_id=external_idp_id,
            domain_preferences=DomainPreferences(),
        )
        return self._map_to_schema(new_user)

    @validate_call
    def update_preferences(
        self, user_id: InternalUserId, patch: DomainPreferencesUpdate
    ) -> UserRead | None:
        updated_user = self.repo.update_preferences(user_id=user_id, patch=patch)
        if updated_user is None:
            return None
        return self._map_to_schema(updated_user)
