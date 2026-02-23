from pydantic import BaseModel, ConfigDict, Field


class BookBase(BaseModel):
    title: str
    authors: list[str] = Field(default_factory=list)
    genres: list[str] = Field(default_factory=list)
    publication_year: int | None = None


class BookRead(BookBase):
    id: str

    model_config = ConfigDict(from_attributes=True)


class PaginatedBooks(BaseModel):
    items: list[BookRead]
    total: int
    page: int
    size: int
