import argparse
import logging
from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import UTC, datetime
from typing import TypedDict

from sqlalchemy import delete, desc, select
from sqlalchemy.orm import Session

from books_rec_api.database import SessionLocal
from books_rec_api.domain import BookId, PopularityScope, RecsVersion
from books_rec_api.models import Book, BookPopularity

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PopularityRecord(TypedDict):
    scope: PopularityScope
    book_ids: list[BookId]
    recs_version: RecsVersion
    updated_at: datetime


def compute_popularity(
    session_factory: Callable[[], AbstractContextManager[Session]] = SessionLocal,
) -> None:
    logger.info("Computing global popularity...")

    with session_factory() as session:
        # Simple heuristic: top 1000 books by ratings_count
        stmt = (
            select(Book.id)
            .where(Book.ratings_count.is_not(None))
            .order_by(desc(Book.ratings_count))
            .limit(1000)
        )
        popular_ids_raw = session.scalars(stmt).all()

        if not popular_ids_raw:
            logger.warning("No popular books found.")
            return

        popular_ids = [BookId(pid) for pid in popular_ids_raw]
        recs_version = RecsVersion(datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"))

        record = PopularityRecord(
            scope="global",
            book_ids=popular_ids,
            recs_version=recs_version,
            updated_at=datetime.now(UTC),
        )

        # Wipe existing global scope
        session.execute(delete(BookPopularity).where(BookPopularity.scope == record["scope"]))

        # Insert new popularity row
        new_popularity = BookPopularity(**record)
        session.add(new_popularity)
        session.commit()

        logger.info(f"Saved {len(popular_ids)} popular books with version {recs_version}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compute global book popularity.")
    parser.parse_args()
    compute_popularity()
