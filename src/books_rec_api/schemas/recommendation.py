from pydantic import BaseModel


class Book(BaseModel):
    title: str
    author: str
    cover_url: str


class Recommendation(BaseModel):
    book_id: str
    score: float
    reason: str
    book: Book


class RecommendationsResponse(BaseModel):
    recommendations: list[Recommendation]
