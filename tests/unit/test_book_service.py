from unittest.mock import MagicMock

from books_rec_api.models import Book, BookPopularity, BookSimilarity
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


def test_get_similar_books_full_neighbors():
    repo = MagicMock()
    # Mock book existence
    repo.get_by_id.return_value = Book(id="A")

    # Mock similarities
    repo.get_similarities.return_value = BookSimilarity(
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
    assert result.similar_book_ids == ["B", "C"]  # Limit 2
    assert result.algo_id == "meta_v0"
    assert result.recs_version == "v1"
    repo.get_popularity.assert_not_called()


def test_get_similar_books_fallback_needed():
    repo = MagicMock()
    repo.get_by_id.return_value = Book(id="A")

    # Only 1 neighbor
    repo.get_similarities.return_value = BookSimilarity(
        book_id="A",
        neighbor_ids=["B"],
        algo_id="meta_v0",
        recs_version="v1",
    )
    # Popularity list
    repo.get_popularity.return_value = BookPopularity(
        scope="global",
        book_ids=["P1", "P2", "P3"],
        recs_version="pop_v1",
    )

    svc = BookService(repo)
    result = svc.get_similar_books(book_id="A", limit=3, trace_id="trace-123")

    assert result is not None
    assert result.similar_book_ids == ["B", "P1", "P2"]  # 1 neighbor + 2 fallback
    assert result.recs_version == "v1"  # Keeps neighbor version if present


def test_get_similar_books_deduplication():
    repo = MagicMock()
    repo.get_by_id.return_value = Book(id="A")

    repo.get_similarities.return_value = BookSimilarity(
        book_id="A",
        neighbor_ids=["B", "A", "C"],  # Includes anchor 'A'
    )
    repo.get_popularity.return_value = BookPopularity(
        scope="global",
        book_ids=["C", "D", "A"],  # Includes 'C' (in neighbors) and 'A' (anchor)
    )

    svc = BookService(repo)
    result = svc.get_similar_books(book_id="A", limit=10, trace_id="trace-123")

    # Should remove A, and keep unique B, C, D
    assert result.similar_book_ids == ["B", "C", "D"]


def test_get_similar_books_not_found():
    repo = MagicMock()
    repo.get_by_id.return_value = None  # Book doesn't exist

    svc = BookService(repo)
    result = svc.get_similar_books(book_id="missing", limit=10, trace_id="trace-123")

    assert result is None


def test_get_similar_books_no_similarities_no_popularity():
    repo = MagicMock()
    repo.get_by_id.return_value = Book(id="A")
    repo.get_similarities.return_value = None
    repo.get_popularity.return_value = None

    svc = BookService(repo)
    result = svc.get_similar_books(book_id="A", limit=10, trace_id="trace-123")

    assert result is not None
    assert result.similar_book_ids == []
    assert result.recs_version is None
    assert result.algo_id is None


def test_get_similar_books_recs_version_fallback():
    repo = MagicMock()
    repo.get_by_id.return_value = Book(id="A")
    # Similarities exist but without a recs_version
    repo.get_similarities.return_value = BookSimilarity(
        book_id="A",
        neighbor_ids=["B"],
        algo_id="meta_v0",
        recs_version=None,
    )
    repo.get_popularity.return_value = BookPopularity(
        scope="global",
        book_ids=["C", "D"],
        recs_version="pop_v2",
    )

    svc = BookService(repo)
    result = svc.get_similar_books(book_id="A", limit=3, trace_id="trace-123")

    assert result is not None
    assert result.similar_book_ids == ["B", "C", "D"]
    assert result.recs_version == "pop_v2"


def test_get_similar_books_exact_limit():
    repo = MagicMock()
    repo.get_by_id.return_value = Book(id="A")

    repo.get_similarities.return_value = BookSimilarity(
        book_id="A",
        neighbor_ids=["B", "C"],
    )
    repo.get_popularity.return_value = BookPopularity(
        scope="global",
        book_ids=["D"],
    )

    svc = BookService(repo)
    # Request exactly 2, which matches neighbor count exactly
    result = svc.get_similar_books(book_id="A", limit=2, trace_id="trace-123")

    assert result is not None
    assert result.similar_book_ids == ["B", "C"]
    repo.get_popularity.assert_not_called()


def test_get_similar_books_catalog_exhaustion():
    repo = MagicMock()
    repo.get_by_id.return_value = Book(id="A")

    repo.get_similarities.return_value = BookSimilarity(
        book_id="A",
        neighbor_ids=["B"],
    )
    repo.get_popularity.return_value = BookPopularity(
        scope="global",
        book_ids=["C", "D"],
    )

    svc = BookService(repo)
    # Request 100, but only 3 exist in total
    result = svc.get_similar_books(book_id="A", limit=100, trace_id="trace-123")

    assert result is not None
    assert result.similar_book_ids == ["B", "C", "D"]


def test_get_similar_books_total_deduplication():
    repo = MagicMock()
    repo.get_by_id.return_value = Book(id="A")

    repo.get_similarities.return_value = BookSimilarity(
        book_id="A",
        neighbor_ids=["B", "C"],
    )
    repo.get_popularity.return_value = BookPopularity(
        scope="global",
        book_ids=["C", "B", "A"],  # All popular are already neighbors or anchor
    )

    svc = BookService(repo)
    # Limit is 5, but after dedup we should only get the 2 neighbors
    result = svc.get_similar_books(book_id="A", limit=5, trace_id="trace-123")

    assert result is not None
    assert result.similar_book_ids == ["B", "C"]
