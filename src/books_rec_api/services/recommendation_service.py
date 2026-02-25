from books_rec_api.domain import BookId, Score
from books_rec_api.schemas.recommendation import Book, Recommendation
from books_rec_api.schemas.user import UserRead


def get_recommendations(*, user: UserRead) -> list[Recommendation]:
    _ = user
    # MVP stub: replace with real ranking logic + data retrieval.
    return [
        Recommendation(
            book_id=BookId("123"),
            score=Score(0.95),
            reason="popular_in_sci_fi",
            book=Book(
                title="Dune",
                author="Frank Herbert",
                cover_url="https://example.com/dune.jpg",
            ),
        )
    ]
