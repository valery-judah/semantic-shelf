from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from books_rec_api.domain import BookId, PopularityScope
from books_rec_api.models import Book, BookPopularity, BookSimilarity


class BooksRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, book_id: BookId) -> Book | None:
        return self.session.get(Book, book_id)

    def list_books(
        self, limit: int = 20, offset: int = 0, genre: str | None = None
    ) -> tuple[Sequence[Book], int]:
        """
        Returns a tuple of (items, total_count).
        """
        stmt = select(Book)
        count_stmt = select(func.count()).select_from(Book)

        if genre:
            from sqlalchemy import String

            stmt = stmt.where(Book.genres.cast(String).like(f'%"{genre}"%'))
            count_stmt = count_stmt.where(Book.genres.cast(String).like(f'%"{genre}"%'))

        stmt = stmt.limit(limit).offset(offset)

        total = self.session.execute(count_stmt).scalar_one()
        items = self.session.scalars(stmt).all()

        return items, total

    def get_similarities(self, book_id: BookId) -> BookSimilarity | None:
        """
        Retrieves the pre-computed similarities for a given book.
        """
        return self.session.get(BookSimilarity, book_id)

    def get_popularity(self, scope: PopularityScope = "global") -> BookPopularity | None:
        """
        Retrieves the pre-computed popularity list.
        """
        return self.session.get(BookPopularity, scope)
