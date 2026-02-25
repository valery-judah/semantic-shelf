import argparse
import logging
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import NamedTuple, TypedDict

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from books_rec_api.database import SessionLocal
from books_rec_api.domain import AlgoId, BookId, RecsVersion, Score
from books_rec_api.models import Book, BookSimilarity

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class BookFeatures:
    authors: frozenset[str]
    genres: frozenset[str]


class NeighborScore(NamedTuple):
    book_id: BookId
    score: Score


class SimilarityRecord(TypedDict):
    book_id: BookId
    neighbor_ids: list[BookId]
    recs_version: RecsVersion
    algo_id: AlgoId
    updated_at: datetime


def normalize_metadata(items: list[str] | None) -> frozenset[str]:
    if not items:
        return frozenset()
    return frozenset(item.strip() for item in items if item and item.strip())


def compute_jaccard(set1: frozenset[str], set2: frozenset[str]) -> float:
    if not set1 and not set2:
        return 0.0
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    return intersection / union


def compute_neighbors(
    k: int = 100, session_factory: Callable[[], AbstractContextManager[Session]] = SessionLocal
) -> None:
    logger.info("Fetching book metadata...")

    with session_factory() as session:
        stmt = select(Book.id, Book.authors, Book.genres)
        books = session.execute(stmt).all()

        if not books:
            logger.warning("No books found.")
            return

        logger.info(f"Loaded {len(books)} books. Computing similarities...")

        # Precompute features
        book_data: dict[BookId, BookFeatures] = {}
        for b in books:
            book_id = BookId(b.id)
            book_data[book_id] = BookFeatures(
                authors=normalize_metadata(b.authors),
                genres=normalize_metadata(b.genres),
            )

        book_ids = list(book_data.keys())
        recs_version = RecsVersion(datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"))
        algo_id = AlgoId("meta_v0")

        similarities_to_insert: list[SimilarityRecord] = []

        # Simple O(N^2) pairwise similarity
        for i, anchor_id in enumerate(book_ids):
            anchor = book_data[anchor_id]
            scores: list[NeighborScore] = []

            for candidate_id in book_ids:
                if anchor_id == candidate_id:
                    continue
                candidate = book_data[candidate_id]

                # Weight authors more heavily than genres
                author_sim = compute_jaccard(anchor.authors, candidate.authors)
                genre_sim = compute_jaccard(anchor.genres, candidate.genres)

                # Simple weighted score
                raw_score = (author_sim * 0.7) + (genre_sim * 0.3)
                if raw_score > 0:
                    scores.append(NeighborScore(book_id=candidate_id, score=Score(raw_score)))

            # Sort by score descending, keep top K, determinism by candidate id
            scores.sort(key=lambda x: (-x.score, x.book_id))
            top_k_ids = [ns.book_id for ns in scores[:k]]

            similarities_to_insert.append(
                SimilarityRecord(
                    book_id=anchor_id,
                    neighbor_ids=top_k_ids,
                    recs_version=recs_version,
                    algo_id=algo_id,
                    updated_at=datetime.now(UTC),
                )
            )

            if (i + 1) % 1000 == 0:
                logger.info(f"Computed {i + 1}/{len(book_ids)} books.")

        logger.info("Storing similarities...")

        # Batch upsert to database
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
