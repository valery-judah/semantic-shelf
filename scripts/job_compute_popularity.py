import argparse
import logging
from datetime import UTC, datetime

from sqlalchemy import delete, desc, select

from books_rec_api.database import SessionLocal
from books_rec_api.models import Book, BookPopularity

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def compute_popularity() -> None:
    logger.info("Computing global popularity...")

    with SessionLocal() as session:
        # Simple heuristic: top 1000 books by ratings_count
        stmt = (
            select(Book.id)
            .where(Book.ratings_count.is_not(None))
            .order_by(desc(Book.ratings_count))
            .limit(1000)
        )
        popular_ids = session.scalars(stmt).all()

        if not popular_ids:
            logger.warning("No popular books found.")
            return

        recs_version = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Wipe existing global scope
        session.execute(delete(BookPopularity).where(BookPopularity.scope == "global"))

        # Insert new popularity row
        new_popularity = BookPopularity(
            scope="global",
            book_ids=list(popular_ids),
            recs_version=recs_version,
            updated_at=datetime.now(UTC),
        )
        session.add(new_popularity)
        session.commit()

        logger.info(f"Saved {len(popular_ids)} popular books with version {recs_version}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compute global book popularity.")
    parser.parse_args()
    compute_popularity()
