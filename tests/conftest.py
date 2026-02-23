from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from books_rec_api.dependencies.auth import get_external_idp_id
from books_rec_api.dependencies.users import get_user_service
from books_rec_api.main import app
from books_rec_api.repositories.users_repository import UsersRepository
from books_rec_api.services.user_service import UserService


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def test_external_idp_id() -> str:
    return "auth0|test_user_123"


@pytest.fixture
def mock_repo() -> UsersRepository:
    return UsersRepository()


@pytest.fixture
def mock_user_service(mock_repo: UsersRepository) -> UserService:
    return UserService(repo=mock_repo)


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def client_with_overrides(
    test_external_idp_id: str, mock_user_service: UserService
) -> Iterator[TestClient]:
    def override_get_external_id() -> str:
        return test_external_idp_id

    def override_get_user_service() -> UserService:
        return mock_user_service

    app.dependency_overrides[get_external_idp_id] = override_get_external_id
    app.dependency_overrides[get_user_service] = override_get_user_service

    with TestClient(app) as test_client:
        yield test_client
