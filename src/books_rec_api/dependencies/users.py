from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from books_rec_api.database import SessionLocal
from books_rec_api.repositories.users_repository import UsersRepository
from books_rec_api.services.user_service import UserService


def get_db_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_users_repository(session: Annotated[Session, Depends(get_db_session)]) -> UsersRepository:
    return UsersRepository(session=session)


def get_user_service(
    repo: Annotated[UsersRepository, Depends(get_users_repository)],
) -> UserService:
    return UserService(repo=repo)
