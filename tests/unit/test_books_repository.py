from unittest.mock import MagicMock

from books_rec_api.models import Book
from books_rec_api.repositories.books_repository import BooksRepository


def test_get_by_id_returns_book():
    session = MagicMock()
    book = Book(
        id="1", title="Dune", authors=["Frank Herbert"], genres=["sci-fi"], publication_year=1965
    )
    session.get.return_value = book

    repo = BooksRepository(session)
    result = repo.get_by_id("1")

    assert result == book
    session.get.assert_called_once_with(Book, "1")


def test_get_by_id_returns_none():
    session = MagicMock()
    session.get.return_value = None

    repo = BooksRepository(session)
    result = repo.get_by_id("999")

    assert result is None
    session.get.assert_called_once_with(Book, "999")
