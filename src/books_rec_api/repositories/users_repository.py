from books_rec_api.schemas.user import DomainPreferences, DomainPreferencesUpdate, UserRead


class UsersRepository:
    def __init__(self) -> None:
        self._by_id: dict[str, UserRead] = {}
        self._id_by_external: dict[str, str] = {}

    def get_by_external_id(self, external_idp_id: str) -> UserRead | None:
        user_id = self._id_by_external.get(external_idp_id)
        if user_id is None:
            return None
        return self._by_id.get(user_id)

    def get_by_id(self, user_id: str) -> UserRead | None:
        return self._by_id.get(user_id)

    def create(
        self, id: str, external_idp_id: str, domain_preferences: DomainPreferences
    ) -> UserRead:
        user = UserRead(
            id=id,
            external_idp_id=external_idp_id,
            domain_preferences=domain_preferences,
        )
        self._by_id[id] = user
        self._id_by_external[external_idp_id] = id
        return user

    def update_preferences(self, user_id: str, patch: DomainPreferencesUpdate) -> UserRead | None:
        existing = self._by_id.get(user_id)
        if existing is None:
            return None

        update_data = patch.model_dump(exclude_unset=True, exclude_none=True)
        if not update_data:
            return existing

        merged_preferences = existing.domain_preferences.model_copy(update=update_data)
        updated = existing.model_copy(update={"domain_preferences": merged_preferences})
        self._by_id[user_id] = updated
        return updated
