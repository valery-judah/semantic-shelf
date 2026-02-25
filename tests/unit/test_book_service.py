from unittest.mock import create_autospec

from books_rec_api.models import Book, BookPopularity, BookSimilarity
from books_rec_api.repositories.books_repository import BooksRepository
from books_rec_api.services.book_service import BookService


def make_repo() -> BooksRepository:
    return create_autospec(BooksRepository, instance=True, spec_set=True)


def make_book(book_id: str = "1", title: str = "Dune") -> Book:
    return Book(
        id=book_id,
        title=title,
        authors=["Frank Herbert"],
        genres=["sci-fi"],
        publication_year=1965,
        description="A science fiction epic on Arrakis.",
    )


def make_similarity(
    book_id: str = "A",
    neighbor_ids: list[str] | None = None,
    algo_id: str | None = None,
    recs_version: str | None = None,
) -> BookSimilarity:
    return BookSimilarity(
        book_id=book_id,
        neighbor_ids=neighbor_ids or [],
        algo_id=algo_id,
        recs_version=recs_version,
    )


def make_popularity(
    book_ids: list[str] | None = None,
    recs_version: str | None = None,
) -> BookPopularity:
    return BookPopularity(scope="global", book_ids=book_ids or [], recs_version=recs_version)


def test_get_book_returns_schema():
    repo = make_repo()
    book = make_book(book_id="1")
    repo.get_by_id.return_value = book

    svc = BookService(repo)
    result = svc.get_book("1")

    assert result is not None
    assert result.id == "1"
    assert result.title == "Dune"
    assert result.description == "A science fiction epic on Arrakis."
    repo.get_by_id.assert_called_once_with("1")


def test_get_book_returns_none():
    repo = make_repo()
    repo.get_by_id.return_value = None

    svc = BookService(repo)
    result = svc.get_book("999")

    assert result is None
    repo.get_by_id.assert_called_once_with("999")


def test_get_books_paginated():
    repo = make_repo()
    book = make_book(book_id="1")
    repo.list_books.return_value = ([book], 1)

    svc = BookService(repo)
    result = svc.get_books(page=1, size=20)

    assert result.total == 1
    assert result.page == 1
    assert result.size == 20
    assert len(result.items) == 1
    assert result.items[0].id == "1"

    repo.list_books.assert_called_once_with(limit=20, offset=0, genre=None)


def test_get_similar_books_full_neighbors():
    repo = make_repo()
    repo.get_by_id.return_value = make_book(book_id="A")
    repo.get_similarities.return_value = make_similarity(
        book_id="A",
        neighbor_ids=["B", "C", "D"],
        algo_id="meta_v0",
        recs_version="v1",
    )

    svc = BookService(repo)
    result = svc.get_similar_books(book_id="A", limit=2, trace_id="trace-123")

    assert result is not None
    assert result.book_id == "A"
    assert result.trace_id == "trace-123"
    assert result.similar_book_ids == ["B", "C"]
    assert result.algo_id == "meta_v0"
    assert result.recs_version == "v1"
    repo.get_by_id.assert_called_once_with("A")
    repo.get_similarities.assert_called_once_with("A")
    repo.get_popularity.assert_not_called()


def test_get_similar_books_fallback_needed():
    repo = make_repo()
    repo.get_by_id.return_value = make_book(book_id="A")
    repo.get_similarities.return_value = make_similarity(
        book_id="A",
        neighbor_ids=["B"],
        algo_id="meta_v0",
        recs_version="v1",
    )
    repo.get_popularity.return_value = make_popularity(
        book_ids=["P1", "P2", "P3"],
        recs_version="pop_v1",
    )

    svc = BookService(repo)
    result = svc.get_similar_books(book_id="A", limit=3, trace_id="trace-123")

    assert result is not None
    assert result.similar_book_ids == ["B", "P1", "P2"]
    assert result.recs_version == "v1"
    repo.get_by_id.assert_called_once_with("A")
    repo.get_similarities.assert_called_once_with("A")
    repo.get_popularity.assert_called_once_with(scope="global")


def test_get_similar_books_deduplication():
    repo = make_repo()
    repo.get_by_id.return_value = make_book(book_id="A")
    repo.get_similarities.return_value = make_similarity(
        book_id="A",
        neighbor_ids=["B", "A", "C"],
    )
    repo.get_popularity.return_value = make_popularity(book_ids=["C", "D", "A"])

    svc = BookService(repo)
    result = svc.get_similar_books(book_id="A", limit=10, trace_id="trace-123")

    assert result.similar_book_ids == ["B", "C", "D"]
    repo.get_by_id.assert_called_once_with("A")
    repo.get_similarities.assert_called_once_with("A")
    repo.get_popularity.assert_called_once_with(scope="global")


def test_get_similar_books_not_found():
    repo = make_repo()
    repo.get_by_id.return_value = None

    svc = BookService(repo)
    result = svc.get_similar_books(book_id="missing", limit=10, trace_id="trace-123")

    assert result is None
    repo.get_by_id.assert_called_once_with("missing")
    repo.get_similarities.assert_not_called()
    repo.get_popularity.assert_not_called()


def test_get_similar_books_no_similarities_no_popularity():
    repo = make_repo()
    repo.get_by_id.return_value = make_book(book_id="A")
    repo.get_similarities.return_value = None
    repo.get_popularity.return_value = None

    svc = BookService(repo)
    result = svc.get_similar_books(book_id="A", limit=10, trace_id="trace-123")

    assert result is not None
    assert result.similar_book_ids == []
    assert result.recs_version is None
    assert result.algo_id is None
    repo.get_by_id.assert_called_once_with("A")
    repo.get_similarities.assert_called_once_with("A")
    repo.get_popularity.assert_called_once_with(scope="global")


def test_get_similar_books_recs_version_fallback():
    repo = make_repo()
    repo.get_by_id.return_value = make_book(book_id="A")
    repo.get_similarities.return_value = make_similarity(
        book_id="A",
        neighbor_ids=["B"],
        algo_id="meta_v0",
        recs_version=None,
    )
    repo.get_popularity.return_value = make_popularity(
        book_ids=["C", "D"],
        recs_version="pop_v2",
    )

    svc = BookService(repo)
    result = svc.get_similar_books(book_id="A", limit=3, trace_id="trace-123")

    assert result is not None
    assert result.similar_book_ids == ["B", "C", "D"]
    assert result.recs_version == "pop_v2"
    repo.get_by_id.assert_called_once_with("A")
    repo.get_similarities.assert_called_once_with("A")
    repo.get_popularity.assert_called_once_with(scope="global")


def test_get_similar_books_exact_limit():
    repo = make_repo()
    repo.get_by_id.return_value = make_book(book_id="A")
    repo.get_similarities.return_value = make_similarity(book_id="A", neighbor_ids=["B", "C"])
    repo.get_popularity.return_value = make_popularity(book_ids=["D"])

    svc = BookService(repo)
    result = svc.get_similar_books(book_id="A", limit=2, trace_id="trace-123")

    assert result is not None
    assert result.similar_book_ids == ["B", "C"]
    repo.get_by_id.assert_called_once_with("A")
    repo.get_similarities.assert_called_once_with("A")
    repo.get_popularity.assert_not_called()


def test_get_similar_books_catalog_exhaustion():
    repo = make_repo()
    repo.get_by_id.return_value = make_book(book_id="A")
    repo.get_similarities.return_value = make_similarity(book_id="A", neighbor_ids=["B"])
    repo.get_popularity.return_value = make_popularity(book_ids=["C", "D"])

    svc = BookService(repo)
    result = svc.get_similar_books(book_id="A", limit=100, trace_id="trace-123")

    assert result is not None
    assert result.similar_book_ids == ["B", "C", "D"]
    repo.get_by_id.assert_called_once_with("A")
    repo.get_similarities.assert_called_once_with("A")
    repo.get_popularity.assert_called_once_with(scope="global")


def test_get_similar_books_total_deduplication():
    repo = make_repo()
    repo.get_by_id.return_value = make_book(book_id="A")
    repo.get_similarities.return_value = make_similarity(book_id="A", neighbor_ids=["B", "C"])
    repo.get_popularity.return_value = make_popularity(book_ids=["C", "B", "A"])

    svc = BookService(repo)
    result = svc.get_similar_books(book_id="A", limit=5, trace_id="trace-123")

    assert result is not None
    assert result.similar_book_ids == ["B", "C"]
    repo.get_by_id.assert_called_once_with("A")
    repo.get_similarities.assert_called_once_with("A")
    repo.get_popularity.assert_called_once_with(scope="global")
