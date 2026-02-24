from unittest.mock import MagicMock

from books_rec_api.models import Book
from books_rec_api.services.book_service import BookService


def test_get_book_returns_schema():
    repo = MagicMock()
    book = Book(
        id="1",
        title="Dune",
        authors=["Frank Herbert"],
        genres=["sci-fi"],
        publication_year=1965,
        description="A science fiction epic on Arrakis.",
    )
    repo.get_by_id.return_value = book

    svc = BookService(repo)
    result = svc.get_book("1")

    assert result is not None
    assert result.id == "1"
    assert result.title == "Dune"
    assert result.description == "A science fiction epic on Arrakis."
    repo.get_by_id.assert_called_once_with("1")


def test_get_book_returns_none():
    repo = MagicMock()
    repo.get_by_id.return_value = None

    svc = BookService(repo)
    result = svc.get_book("999")

    assert result is None
    repo.get_by_id.assert_called_once_with("999")


def test_get_books_paginated():
    repo = MagicMock()
    book = Book(
        id="1",
        title="Dune",
        authors=["Frank Herbert"],
        genres=["sci-fi"],
        publication_year=1965,
        description="A science fiction epic on Arrakis.",
    )
    repo.list_books.return_value = ([book], 1)

    svc = BookService(repo)
    result = svc.get_books(page=1, size=20)

    assert result.total == 1
    assert result.page == 1
    assert result.size == 20
    assert len(result.items) == 1
    assert result.items[0].id == "1"

    repo.list_books.assert_called_once_with(limit=20, offset=0, genre=None)
