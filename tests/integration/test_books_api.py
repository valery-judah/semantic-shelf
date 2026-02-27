import pytest
from fastapi.testclient import TestClient

from tests.integration.conftest import DataFactory


@pytest.fixture
def sample_books(test_data: DataFactory):
    book1 = test_data.create_book(
        id="book-1",
        title="Dune",
        authors=["Frank Herbert"],
        genres=["sci-fi"],
        publication_year=1965,
        description="A science fiction epic on Arrakis.",
    )
    book2 = test_data.create_book(
        id="book-2",
        title="Foundation",
        authors=["Isaac Asimov"],
        genres=["sci-fi", "classic"],
        publication_year=1951,
    )
    test_data.commit()
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
    assert data["description"] == "A science fiction epic on Arrakis."


def test_get_book_by_id_not_found(client_with_overrides: TestClient):
    response = client_with_overrides.get("/books/nonexistent-book")

    assert response.status_code == 404
    assert response.json()["detail"] == "Book with id nonexistent-book not found"
