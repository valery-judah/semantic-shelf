from books_rec_api.schemas.user import DomainPreferencesUpdate
from books_rec_api.services.user_service import UserService


def test_jit_provisioning_creates_user(mock_user_service: UserService) -> None:
    test_ext_id = "test_sub_001"

    user = mock_user_service.get_or_create_shadow_user(test_ext_id)

    assert user.external_idp_id == test_ext_id
    assert user.id.startswith("usr_")
    assert user.domain_preferences.ui_theme == "dark"


def test_jit_provisioning_returns_existing_user(mock_user_service: UserService) -> None:
    test_ext_id = "test_sub_002"

    first = mock_user_service.get_or_create_shadow_user(test_ext_id)
    second = mock_user_service.get_or_create_shadow_user(test_ext_id)

    assert first.id == second.id


def test_update_preferences_delegates_and_returns_updated_user(
    mock_user_service: UserService,
) -> None:
    test_ext_id = "test_sub_003"
    user = mock_user_service.get_or_create_shadow_user(test_ext_id)

    updated = mock_user_service.update_preferences(
        user_id=user.id,
        patch=DomainPreferencesUpdate(ui_theme="light"),
    )

    assert updated is not None
    assert updated.domain_preferences.ui_theme == "light"
