import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from books_rec_api.models import Book, BookPopularity, BookSimilarity


@pytest.fixture
def sample_books_and_similarities(db_session: Session):
    # Create books
    books = [Book(id=f"book-{i}", title=f"Book {i}") for i in range(1, 10)]
    db_session.add_all(books)

    # Create similarities for book-1
    sim = BookSimilarity(
        book_id="book-1",
        neighbor_ids=["book-2", "book-3"],
        recs_version="v1",
        algo_id="meta_v0",
    )
    db_session.add(sim)

    # Create popularity fallback
    pop = BookPopularity(
        scope="global",
        book_ids=["book-4", "book-5", "book-6"],
        recs_version="pop_v1",
    )
    db_session.add(pop)

    db_session.commit()
    return books


@pytest.fixture
def sample_books_with_anchor_and_duplicates(db_session: Session):
    books = [Book(id=f"book-{i}", title=f"Book {i}") for i in range(1, 10)]
    db_session.add_all(books)

    sim = BookSimilarity(
        book_id="book-1",
        neighbor_ids=["book-2", "book-1", "book-3"],
        recs_version="v2",
        algo_id="meta_v0",
    )
    db_session.add(sim)

    pop = BookPopularity(
        scope="global",
        book_ids=["book-3", "book-4", "book-1", "book-5"],
        recs_version="pop_v2",
    )
    db_session.add(pop)

    db_session.commit()
    return books


def test_get_similar_books_success(
    client_with_overrides: TestClient, sample_books_and_similarities
):
    response = client_with_overrides.get("/books/book-1/similar?limit=4")

    assert response.status_code == 200
    data = response.json()
    assert data["book_id"] == "book-1"
    assert "trace_id" in data
    # book-2, book-3 from neighbors + book-4, book-5 from popularity = 4 total
    assert data["similar_book_ids"] == ["book-2", "book-3", "book-4", "book-5"]
    assert data["algo_id"] == "meta_v0"


def test_get_similar_books_not_found(client_with_overrides: TestClient):
    response = client_with_overrides.get("/books/nonexistent/similar")
    assert response.status_code == 404


def test_get_similar_books_limit_zero(
    client_with_overrides: TestClient, sample_books_and_similarities
):
    response = client_with_overrides.get("/books/book-1/similar?limit=0")

    assert response.status_code == 200
    data = response.json()
    assert data["similar_book_ids"] == []


def test_get_similar_books_only_fallback(
    client_with_overrides: TestClient, sample_books_and_similarities
):
    # book-8 has no neighbors defined
    response = client_with_overrides.get("/books/book-8/similar?limit=2")

    assert response.status_code == 200
    data = response.json()
    # Should come from popularity: book-4, book-5
    assert data["similar_book_ids"] == ["book-4", "book-5"]
    # Should use popularity recs_version if no neighbors found
    assert data["recs_version"] == "pop_v1"


def test_get_similar_books_excludes_anchor_and_deduplicates_api_contract(
    client_with_overrides: TestClient, sample_books_with_anchor_and_duplicates
):
    response = client_with_overrides.get("/books/book-1/similar?limit=5")

    assert response.status_code == 200
    data = response.json()
    assert data["similar_book_ids"] == ["book-2", "book-3", "book-4", "book-5"]
    assert "book-1" not in data["similar_book_ids"]
    assert len(data["similar_book_ids"]) == len(set(data["similar_book_ids"]))


def test_get_similar_books_invalid_limit_below_min(
    client_with_overrides: TestClient, sample_books_and_similarities
):
    response = client_with_overrides.get("/books/book-1/similar?limit=-1")
    assert response.status_code == 400


def test_get_similar_books_invalid_limit_above_max(
    client_with_overrides: TestClient, sample_books_and_similarities
):
    response = client_with_overrides.get("/books/book-1/similar?limit=101")
    assert response.status_code == 400
