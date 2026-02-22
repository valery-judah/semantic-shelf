from books_rec_api.schemas.recommendation import Book, Recommendation


def get_recommendations() -> list[Recommendation]:
    # MVP stub: replace with real ranking logic + data retrieval.
    return [
        Recommendation(
            book_id="123",
            score=0.95,
            reason="popular_in_sci_fi",
            book=Book(
                title="Dune",
                author="Frank Herbert",
                cover_url="https://example.com/dune.jpg",
            ),
        )
    ]
