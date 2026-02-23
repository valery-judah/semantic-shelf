from books_rec_api.repositories.books_repository import BooksRepository
from books_rec_api.schemas.book import BookRead, PaginatedBooks


class BookService:
    def __init__(self, repo: BooksRepository) -> None:
        self.repo = repo

    def get_book(self, book_id: str) -> BookRead | None:
        book = self.repo.get_by_id(book_id)
        if not book:
            return None
        return BookRead.model_validate(book)

    def get_books(self, page: int = 1, size: int = 20, genre: str | None = None) -> PaginatedBooks:

        offset = (page - 1) * size
        items, total = self.repo.list_books(limit=size, offset=offset, genre=genre)

        return PaginatedBooks(
            items=[BookRead.model_validate(item) for item in items],
            total=total,
            page=page,
            size=size,
        )
