from unittest.mock import create_autospec

from sqlalchemy.orm import Session

from books_rec_api.domain import BookId
from books_rec_api.models import Book
from books_rec_api.repositories.books_repository import BooksRepository


def test_get_by_id_returns_book():
    session = create_autospec(Session, instance=True, spec_set=True)
    book = Book(
        id="1", title="Dune", authors=["Frank Herbert"], genres=["sci-fi"], publication_year=1965
    )
    session.get.return_value = book

    repo = BooksRepository(session)
    result = repo.get_by_id(BookId("1"))

    assert result == book
    session.get.assert_called_once_with(Book, "1")


def test_get_by_id_returns_none():
    session = create_autospec(Session, instance=True, spec_set=True)
    session.get.return_value = None

    repo = BooksRepository(session)
    result = repo.get_by_id(BookId("999"))

    assert result is None
    session.get.assert_called_once_with(Book, "999")
