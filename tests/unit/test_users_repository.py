from sqlalchemy.orm import Session

from books_rec_api.repositories.users_repository import UsersRepository
from books_rec_api.schemas.user import DomainPreferences, DomainPreferencesUpdate


def test_create_and_get_by_external_id(db_session: Session) -> None:
    repo = UsersRepository(session=db_session)

    created = repo.create(
        id="usr_1",
        external_idp_id="ext_1",
        domain_preferences=DomainPreferences(),
    )
    found = repo.get_by_external_id("ext_1")

    assert found is not None
    assert found.id == created.id
    assert found.external_idp_id == "ext_1"


def test_get_by_id_returns_none_when_missing(db_session: Session) -> None:
    repo = UsersRepository(session=db_session)

    found = repo.get_by_id("missing")

    assert found is None


def test_update_preferences_top_level_merge_semantics(db_session: Session) -> None:
    repo = UsersRepository(session=db_session)
    created = repo.create(
        id="usr_2",
        external_idp_id="ext_2",
        domain_preferences=DomainPreferences(preferred_genres=["scifi"], ui_theme="dark"),
    )

    updated = repo.update_preferences(
        user_id=created.id,
        patch=DomainPreferencesUpdate(preferred_genres=["fantasy"]),
    )

    assert updated is not None
    assert updated.domain_preferences.get("preferred_genres") == ["fantasy"]
    assert updated.domain_preferences.get("ui_theme") == "dark"


def test_update_preferences_returns_unchanged_on_empty_patch(db_session: Session) -> None:
    repo = UsersRepository(session=db_session)
    created = repo.create(
        id="usr_3",
        external_idp_id="ext_3",
        domain_preferences=DomainPreferences(),
    )

    updated = repo.update_preferences(user_id=created.id, patch=DomainPreferencesUpdate())

    assert updated is not None
    assert updated == created


def test_update_preferences_returns_none_for_unknown_user(db_session: Session) -> None:
    repo = UsersRepository(session=db_session)

    updated = repo.update_preferences(
        user_id="missing",
        patch=DomainPreferencesUpdate(ui_theme="light"),
    )

    assert updated is None
