from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from books_rec_api.dependencies.books import get_book_service
from books_rec_api.schemas.book import BookRead, PaginatedBooks
from books_rec_api.services.book_service import BookService

router = APIRouter(prefix="/books", tags=["books"])


@router.get("", response_model=PaginatedBooks)
def list_books(
    svc: Annotated[BookService, Depends(get_book_service)],
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    genre: str | None = Query(None, description="Filter by genre"),
) -> PaginatedBooks:
    """Retrieve a paginated list of books from the catalog."""
    return svc.get_books(page=page, size=size, genre=genre)


@router.get("/{book_id}", response_model=BookRead)
def get_book_by_id(
    book_id: str,
    svc: Annotated[BookService, Depends(get_book_service)],
) -> BookRead:
    """Retrieve a specific book's metadata."""
    book = svc.get_book(book_id)
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with id {book_id} not found",
        )
    return book
