import argparse
import logging
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert

from books_rec_api.database import SessionLocal
from books_rec_api.models import Book, BookSimilarity

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def compute_jaccard(set1: set[str], set2: set[str]) -> float:
    if not set1 and not set2:
        return 0.0
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    return intersection / union


def compute_neighbors(k: int = 100) -> None:
    logger.info("Fetching book metadata...")

    with SessionLocal() as session:
        stmt = select(Book.id, Book.authors, Book.genres)
        books = session.execute(stmt).all()

        if not books:
            logger.warning("No books found.")
            return

        logger.info(f"Loaded {len(books)} books. Computing similarities...")

        # Precompute sets for faster Jaccard
        book_data = {}
        for b in books:
            authors = set(b.authors) if b.authors else set()
            genres = set(b.genres) if b.genres else set()
            book_data[b.id] = {"authors": authors, "genres": genres}

        book_ids = list(book_data.keys())
        recs_version = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        algo_id = "meta_v0"

        similarities_to_insert = []

        # Simple O(N^2) pairwise similarity
        for i, anchor_id in enumerate(book_ids):
            anchor = book_data[anchor_id]
            scores = []

            for candidate_id in book_ids:
                if anchor_id == candidate_id:
                    continue
                candidate = book_data[candidate_id]

                # Weight authors more heavily than genres
                author_sim = compute_jaccard(anchor["authors"], candidate["authors"])
                genre_sim = compute_jaccard(anchor["genres"], candidate["genres"])

                # Simple weighted score
                score = (author_sim * 0.7) + (genre_sim * 0.3)
                if score > 0:
                    scores.append((candidate_id, score))

            # Sort by score descending, keep top K
            scores.sort(key=lambda x: x[1], reverse=True)
            top_k_ids = [candidate_id for candidate_id, _ in scores[:k]]

            similarities_to_insert.append(
                {
                    "book_id": anchor_id,
                    "neighbor_ids": top_k_ids,
                    "recs_version": recs_version,
                    "algo_id": algo_id,
                    "updated_at": datetime.now(UTC),
                }
            )

            if (i + 1) % 1000 == 0:
                logger.info(f"Computed {i + 1}/{len(book_ids)} books.")

        logger.info("Storing similarities...")

        # Batch upsert to database
        # Since we're replacing all, we can just delete all and insert, or use bulk upsert.
        # Deleting all might be easier for MVP
        session.execute(delete(BookSimilarity))

        batch_size = 1000
        for i in range(0, len(similarities_to_insert), batch_size):
            batch = similarities_to_insert[i : i + batch_size]
            session.execute(insert(BookSimilarity).values(batch))

        session.commit()
        logger.info(
            f"Saved similarities for {len(similarities_to_insert)} books. Version: {recs_version}"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compute book neighbors.")
    parser.add_argument("--k", type=int, default=100, help="Max neighbors per book")
    args = parser.parse_args()
    compute_neighbors(k=args.k)
