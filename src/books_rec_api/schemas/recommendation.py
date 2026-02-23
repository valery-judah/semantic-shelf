from pydantic import BaseModel, Field


class Book(BaseModel):
    title: str = Field(description="Title of the book", examples=["Dune"])
    author: str = Field(description="Author of the book", examples=["Frank Herbert"])
    cover_url: str = Field(
        description="URL to the cover image of the book", examples=["https://example.com/dune.jpg"]
    )


class Recommendation(BaseModel):
    book_id: str = Field(
        description="Unique identifier of the recommended book", examples=["book-123"]
    )
    score: float = Field(
        description="Recommendation score, between 0.0 and 1.0", examples=[0.95], ge=0.0, le=1.0
    )
    reason: str = Field(
        description="Explanation for the recommendation",
        examples=["Because you like Science Fiction"],
    )
    book: Book = Field(description="Detailed information about the recommended book")


class RecommendationsResponse(BaseModel):
    recommendations: list[Recommendation] = Field(description="List of recommended books")
