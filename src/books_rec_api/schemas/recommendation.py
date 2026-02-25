from pydantic import BaseModel, Field

from books_rec_api.domain import AlgoId, BookId, RecsVersion, Score


class Book(BaseModel):
    title: str = Field(description="Title of the book", examples=["Dune"])
    author: str = Field(description="Author of the book", examples=["Frank Herbert"])
    cover_url: str = Field(
        description="URL to the cover image of the book", examples=["https://example.com/dune.jpg"]
    )


class Recommendation(BaseModel):
    book_id: BookId = Field(
        description="Unique identifier of the recommended book", examples=["book-123"]
    )
    score: Score = Field(
        description="Recommendation score, between 0.0 and 1.0", examples=[0.95], ge=0.0, le=1.0
    )
    reason: str = Field(
        description="Explanation for the recommendation",
        examples=["Because you like Science Fiction"],
    )
    book: Book = Field(description="Detailed information about the recommended book")


class RecommendationsResponse(BaseModel):
    recommendations: list[Recommendation] = Field(description="List of recommended books")


class SimilarBooksResponse(BaseModel):
    book_id: BookId = Field(
        description="Unique identifier of the anchor book", examples=["book-123"]
    )
    similar_book_ids: list[BookId] = Field(
        description="List of similar book identifiers", examples=[["book-456", "book-789"]]
    )
    trace_id: str = Field(
        description="Correlation identifier for the request", examples=["01J...XYZ"]
    )
    algo_id: AlgoId = Field(
        description="Identifier for the recommendation algorithm",
        examples=["meta_v0"],
    )
    recs_version: RecsVersion = Field(
        description="Version of the published recommendation artifacts",
        examples=["2026-02-25T03:00Z"],
    )
