import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from books_rec_api.models import Book, BookPopularity, BookSimilarity, TelemetryEvent


class DataFactory:
    def __init__(self, session: Session):
        self.session = session

    def create_book(self, id: str, title: str = "Test Book", **kwargs) -> Book:
        b = Book(id=id, title=title, **kwargs)
        self.session.add(b)
        return b

    def create_books(self, count: int, id_prefix: str = "book-") -> list[Book]:
        books = [Book(id=f"{id_prefix}{i}", title=f"Book {i}") for i in range(1, count + 1)]
        self.session.add_all(books)
        return books

    def create_similarity(self, book_id: str, neighbor_ids: list[str], **kwargs) -> BookSimilarity:
        kwargs.setdefault("recs_version", "v1")
        kwargs.setdefault("algo_id", "meta_v0")
        s = BookSimilarity(book_id=book_id, neighbor_ids=neighbor_ids, **kwargs)
        self.session.add(s)
        return s

    def create_popularity(
        self, book_ids: list[str], scope: str = "global", **kwargs
    ) -> BookPopularity:
        kwargs.setdefault("recs_version", "pop_v1")
        p = BookPopularity(scope=scope, book_ids=book_ids, **kwargs)
        self.session.add(p)
        return p

    def get_telemetry_events(self) -> list[TelemetryEvent]:
        return self.session.execute(select(TelemetryEvent)).scalars().all()

    def commit(self):
        self.session.commit()


@pytest.fixture
def test_data(db_session: Session) -> DataFactory:
    return DataFactory(db_session)


@pytest.fixture
def sample_books_and_similarities(test_data: DataFactory):
    books = test_data.create_books(count=9)
    test_data.create_similarity(
        book_id="book-1",
        neighbor_ids=["book-2", "book-3"],
    )
    test_data.create_popularity(
        book_ids=["book-4", "book-5", "book-6"],
    )
    test_data.commit()
    return books


@pytest.fixture
def sample_books_with_anchor_and_duplicates(test_data: DataFactory):
    books = test_data.create_books(count=9)
    test_data.create_similarity(
        book_id="book-1",
        neighbor_ids=["book-2", "book-1", "book-3"],
        recs_version="v2",
    )
    test_data.create_popularity(
        book_ids=["book-3", "book-4", "book-1", "book-5"],
        recs_version="pop_v2",
    )
    test_data.commit()
    return books
