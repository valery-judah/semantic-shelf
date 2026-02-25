from pydantic import BaseModel, ConfigDict, Field

from books_rec_api.domain import BookId


class BookBase(BaseModel):
    title: str
    authors: list[str] = Field(default_factory=list)
    genres: list[str] = Field(default_factory=list)
    publication_year: int | None = None
    description: str | None = None


class BookRead(BookBase):
    id: BookId

    model_config = ConfigDict(from_attributes=True)


class PaginatedBooks(BaseModel):
    items: list[BookRead]
    total: int
    page: int
    size: int
