from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from books_rec_api.dependencies.users import get_db_session
from books_rec_api.repositories.books_repository import BooksRepository
from books_rec_api.services.book_service import BookService


def get_books_repository(session: Annotated[Session, Depends(get_db_session)]) -> BooksRepository:
    return BooksRepository(session=session)


def get_book_service(
    repo: Annotated[BooksRepository, Depends(get_books_repository)],
) -> BookService:
    return BookService(repo=repo)
