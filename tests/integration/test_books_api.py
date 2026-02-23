import pytest
from fastapi.testclient import TestClient

from books_rec_api.models import Book


@pytest.fixture
def sample_books(db_session):
    book1 = Book(
        id="book-1",
        title="Dune",
        authors=["Frank Herbert"],
        genres=["sci-fi"],
        publication_year=1965,
    )
    book2 = Book(
        id="book-2",
        title="Foundation",
        authors=["Isaac Asimov"],
        genres=["sci-fi", "classic"],
        publication_year=1951,
    )
    db_session.add_all([book1, book2])
    db_session.commit()
    return [book1, book2]


def test_list_books(client_with_overrides: TestClient, sample_books):
    response = client_with_overrides.get("/books")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2

    titles = [item["title"] for item in data["items"]]
    assert "Dune" in titles
    assert "Foundation" in titles


def test_list_books_with_genre_filter(client_with_overrides: TestClient, sample_books):
    response = client_with_overrides.get("/books?genre=classic")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["title"] == "Foundation"


def test_get_book_by_id(client_with_overrides: TestClient, sample_books):
    response = client_with_overrides.get("/books/book-1")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "book-1"
    assert data["title"] == "Dune"
    assert data["authors"] == ["Frank Herbert"]


def test_get_book_by_id_not_found(client_with_overrides: TestClient):
    response = client_with_overrides.get("/books/nonexistent-book")

    assert response.status_code == 404
    assert response.json()["detail"] == "Book with id nonexistent-book not found"
