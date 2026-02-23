from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from books_rec_api.database import Base
from books_rec_api.dependencies.auth import get_external_idp_id
from books_rec_api.main import app
from books_rec_api.repositories.users_repository import UsersRepository
from books_rec_api.services.user_service import UserService


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


@pytest.fixture(scope="session")
def db_engine() -> Engine:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(db_engine: Engine) -> Iterator[Session]:
    connection = db_engine.connect()
    transaction = connection.begin()
    session_factory = sessionmaker(bind=connection)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def test_external_idp_id() -> str:
    return "auth0|test_user_123"


@pytest.fixture
def mock_repo(db_session: Session) -> UsersRepository:
    return UsersRepository(session=db_session)


@pytest.fixture
def mock_user_service(mock_repo: UsersRepository) -> UserService:
    return UserService(repo=mock_repo)


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    from books_rec_api.dependencies.users import get_db_session

    def override_get_db_session() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db_session

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def client_with_overrides(client: TestClient, test_external_idp_id: str) -> Iterator[TestClient]:
    def override_get_external_id() -> str:
        return test_external_idp_id

    app.dependency_overrides[get_external_idp_id] = override_get_external_id

    yield client
