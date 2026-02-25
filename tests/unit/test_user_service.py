import pytest
from pydantic import ValidationError

from books_rec_api.domain import InternalUserId
from books_rec_api.schemas.user import DomainPreferencesUpdate
from books_rec_api.services.user_service import UserService


def test_jit_provisioning_creates_user(user_service: UserService) -> None:
    # Given
    test_ext_id = "test_sub_001"

    # When
    user = user_service.get_or_create_shadow_user(test_ext_id)

    # Then
    assert user.external_idp_id == test_ext_id
    assert user.id.startswith("usr_")
    assert user.domain_preferences.ui_theme == "dark"


def test_jit_provisioning_returns_existing_user(user_service: UserService) -> None:
    # Given
    test_ext_id = "test_sub_002"
    first = user_service.get_or_create_shadow_user(test_ext_id)

    # When
    second = user_service.get_or_create_shadow_user(test_ext_id)

    # Then
    assert first.id == second.id


def test_update_preferences_delegates_and_returns_updated_user(
    user_service: UserService,
) -> None:
    # Given
    test_ext_id = "test_sub_003"
    user = user_service.get_or_create_shadow_user(test_ext_id)
    patch = DomainPreferencesUpdate(ui_theme="light")

    # When
    updated = user_service.update_preferences(
        user_id=user.id,
        patch=patch,
    )

    # Then
    assert updated is not None
    assert updated.domain_preferences.ui_theme == "light"


def test_service_validation_rejects_invalid_internal_user_id(user_service: UserService) -> None:
    patch = DomainPreferencesUpdate(ui_theme="light")
    with pytest.raises(ValidationError):
        user_service.update_preferences(
            user_id=InternalUserId("invalid_id"),  # Doesn't start with usr_
            patch=patch,
        )
