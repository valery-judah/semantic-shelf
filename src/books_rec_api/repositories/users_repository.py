from sqlalchemy import select
from sqlalchemy.orm import Session

from books_rec_api.domain import ExternalIdpId, InternalUserId
from books_rec_api.models import User as UserModel
from books_rec_api.schemas.user import DomainPreferences, DomainPreferencesUpdate


class UsersRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_external_id(self, external_idp_id: ExternalIdpId) -> UserModel | None:
        stmt = select(UserModel).where(UserModel.external_idp_id == external_idp_id)
        return self.session.scalars(stmt).first()

    def get_by_id(self, user_id: InternalUserId) -> UserModel | None:
        return self.session.get(UserModel, user_id)

    def create(
        self,
        id: InternalUserId,
        external_idp_id: ExternalIdpId,
        domain_preferences: DomainPreferences,
    ) -> UserModel:
        user_model = UserModel(
            id=id,
            external_idp_id=external_idp_id,
            domain_preferences=domain_preferences.model_dump(),
        )
        self.session.add(user_model)
        self.session.commit()
        self.session.refresh(user_model)

        return user_model

    def update_preferences(
        self, user_id: InternalUserId, patch: DomainPreferencesUpdate
    ) -> UserModel | None:
        user_model = self.session.get(UserModel, user_id)
        if user_model is None:
            return None

        update_data = patch.model_dump(exclude_unset=True, exclude_none=True)
        if not update_data:
            return user_model

        current_prefs = DomainPreferences(**user_model.domain_preferences)
        merged_prefs = current_prefs.model_copy(update=update_data)

        user_model.domain_preferences = merged_prefs.model_dump()
        self.session.commit()
        self.session.refresh(user_model)

        return user_model
