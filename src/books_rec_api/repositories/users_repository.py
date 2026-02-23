from sqlalchemy import select
from sqlalchemy.orm import Session

from books_rec_api.models import User as UserModel
from books_rec_api.schemas.user import DomainPreferences, DomainPreferencesUpdate, UserRead


class UsersRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_external_id(self, external_idp_id: str) -> UserRead | None:
        stmt = select(UserModel).where(UserModel.external_idp_id == external_idp_id)
        user_model = self.session.scalars(stmt).first()
        if user_model is None:
            return None
        return UserRead(
            id=user_model.id,
            external_idp_id=user_model.external_idp_id,
            domain_preferences=DomainPreferences(**user_model.domain_preferences),
        )

    def get_by_id(self, user_id: str) -> UserRead | None:
        user_model = self.session.get(UserModel, user_id)
        if user_model is None:
            return None
        return UserRead(
            id=user_model.id,
            external_idp_id=user_model.external_idp_id,
            domain_preferences=DomainPreferences(**user_model.domain_preferences),
        )

    def create(
        self, id: str, external_idp_id: str, domain_preferences: DomainPreferences
    ) -> UserRead:
        user_model = UserModel(
            id=id,
            external_idp_id=external_idp_id,
            domain_preferences=domain_preferences.model_dump(),
        )
        self.session.add(user_model)
        self.session.commit()
        self.session.refresh(user_model)

        return UserRead(
            id=user_model.id,
            external_idp_id=user_model.external_idp_id,
            domain_preferences=DomainPreferences(**user_model.domain_preferences),
        )

    def update_preferences(self, user_id: str, patch: DomainPreferencesUpdate) -> UserRead | None:
        user_model = self.session.get(UserModel, user_id)
        if user_model is None:
            return None

        update_data = patch.model_dump(exclude_unset=True, exclude_none=True)
        if not update_data:
            return UserRead(
                id=user_model.id,
                external_idp_id=user_model.external_idp_id,
                domain_preferences=DomainPreferences(**user_model.domain_preferences),
            )

        current_prefs = DomainPreferences(**user_model.domain_preferences)
        merged_prefs = current_prefs.model_copy(update=update_data)

        user_model.domain_preferences = merged_prefs.model_dump()
        self.session.commit()
        self.session.refresh(user_model)

        return UserRead(
            id=user_model.id,
            external_idp_id=user_model.external_idp_id,
            domain_preferences=DomainPreferences(**user_model.domain_preferences),
        )
