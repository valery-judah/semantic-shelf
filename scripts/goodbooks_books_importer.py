from __future__ import annotations

import ast
import csv
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from books_rec_api.database import SessionLocal
from books_rec_api.models import Book


@dataclass
class ImportStats:
    total_rows: int = 0
    processed_rows: int = 0
    inserted_rows: int = 0
    updated_rows: int = 0
    skipped_rows: int = 0
    error_rows: int = 0


def parse_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def parse_listish(value: str | None) -> list[str]:
    text_value = parse_optional_text(value)
    if text_value is None:
        return []
    if text_value.startswith("[") and text_value.endswith("]"):
        parsed = ast.literal_eval(text_value)
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
        raise ValueError(f"List field is not a list: {text_value!r}")
    return [part.strip() for part in text_value.split(",") if part.strip()]


def parse_optional_int(value: str | None) -> int | None:
    text_value = parse_optional_text(value)
    if text_value is None:
        return None
    try:
        return int(Decimal(text_value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Invalid integer value: {text_value!r}") from exc


def parse_optional_decimal(value: str | None) -> Decimal | None:
    text_value = parse_optional_text(value)
    if text_value is None:
        return None
    try:
        return Decimal(text_value)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid decimal value: {text_value!r}") from exc


def map_book_row(row: dict[str, str], *, default_source: str = "goodbooks") -> dict[str, Any]:
    book_id = parse_optional_int(row.get("book_id"))
    title = parse_optional_text(row.get("title"))
    if book_id is None:
        raise ValueError("book_id is required")
    if title is None:
        raise ValueError("title is required")

    return {
        "id": str(book_id),
        "title": title,
        "authors": parse_listish(row.get("authors")),
        "genres": parse_listish(row.get("genres")),
        "publication_year": parse_optional_int(row.get("original_publication_year")),
        "source": parse_optional_text(row.get("source")) or default_source,
        "goodreads_book_id": parse_optional_int(row.get("goodreads_book_id")),
        "best_book_id": parse_optional_int(row.get("best_book_id")),
        "work_id": parse_optional_int(row.get("work_id")),
        "books_count": parse_optional_int(row.get("books_count")),
        "isbn": parse_optional_text(row.get("isbn")),
        "isbn13": parse_optional_text(row.get("isbn13")),
        "language_code": parse_optional_text(row.get("language_code")),
        "average_rating": parse_optional_decimal(row.get("average_rating")),
        "ratings_count": parse_optional_int(row.get("ratings_count")),
        "work_ratings_count": parse_optional_int(row.get("work_ratings_count")),
        "work_text_reviews_count": parse_optional_int(row.get("work_text_reviews_count")),
        "ratings_1": parse_optional_int(row.get("ratings_1")),
        "ratings_2": parse_optional_int(row.get("ratings_2")),
        "ratings_3": parse_optional_int(row.get("ratings_3")),
        "ratings_4": parse_optional_int(row.get("ratings_4")),
        "ratings_5": parse_optional_int(row.get("ratings_5")),
        "original_title": parse_optional_text(row.get("original_title")),
        "description": parse_optional_text(row.get("description")),
        "pages": parse_optional_int(row.get("pages")),
        "publish_date_raw": parse_optional_text(row.get("publishDate")),
        "image_url": parse_optional_text(row.get("image_url")),
        "small_image_url": parse_optional_text(row.get("small_image_url")),
    }


def _books_csv_path(data_dir: Path, use_samples: bool) -> Path:
    return data_dir / "samples" / "books.csv" if use_samples else data_dir / "books_enriched.csv"


def _upsert_books_batch(session: Session, batch: list[dict[str, Any]]) -> tuple[int, int]:
    if not batch:
        return 0, 0

    # PostgreSQL rejects statements above 65535 bind params.
    # We keep each upsert statement well below that ceiling.
    max_rows_per_statement = 1000
    inserted_total = 0
    updated_total = 0
    for start in range(0, len(batch), max_rows_per_statement):
        inserted, updated = _upsert_books_chunk(
            session=session,
            batch=batch[start : start + max_rows_per_statement],
        )
        inserted_total += inserted
        updated_total += updated
    return inserted_total, updated_total


def _upsert_books_chunk(session: Session, batch: list[dict[str, Any]]) -> tuple[int, int]:
    ids = [row["id"] for row in batch]
    existing_ids = set(session.scalars(select(Book.id).where(Book.id.in_(ids))).all())
    inserted = len(ids) - len(existing_ids)
    updated = len(existing_ids)

    stmt = insert(Book).values(batch)
    update_columns = [
        "title",
        "authors",
        "genres",
        "publication_year",
        "source",
        "goodreads_book_id",
        "best_book_id",
        "work_id",
        "books_count",
        "isbn",
        "isbn13",
        "language_code",
        "average_rating",
        "ratings_count",
        "work_ratings_count",
        "work_text_reviews_count",
        "ratings_1",
        "ratings_2",
        "ratings_3",
        "ratings_4",
        "ratings_5",
        "original_title",
        "description",
        "pages",
        "publish_date_raw",
        "image_url",
        "small_image_url",
    ]
    stmt = stmt.on_conflict_do_update(
        index_elements=[Book.id],
        set_={column: getattr(stmt.excluded, column) for column in update_columns},
    )
    session.execute(stmt)
    return inserted, updated


def import_books(
    data_dir: Path | str,
    *,
    use_samples: bool = False,
    truncate_books: bool = False,
    batch_size: int = 1000,
    max_error_logs: int = 20,
) -> ImportStats:
    path = _books_csv_path(Path(data_dir), use_samples=use_samples)
    if not path.exists():
        raise FileNotFoundError(f"Books file not found: {path}")
    if batch_size < 1:
        raise ValueError("batch_size must be >= 1")

    stats = ImportStats()
    session = SessionLocal()
    try:
        with session.begin():
            if truncate_books:
                session.execute(text("TRUNCATE TABLE books"))

            batch: list[dict[str, Any]] = []
            with path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                for row_num, row in enumerate(reader, start=2):
                    stats.total_rows += 1
                    try:
                        mapped = map_book_row(row)
                    except (ValueError, SyntaxError) as exc:
                        stats.error_rows += 1
                        if stats.error_rows <= max_error_logs:
                            print(f"[row {row_num}] parse error: {exc}")
                        continue

                    batch.append(mapped)
                    stats.processed_rows += 1

                    if len(batch) >= batch_size:
                        inserted, updated = _upsert_books_batch(session, batch)
                        stats.inserted_rows += inserted
                        stats.updated_rows += updated
                        batch.clear()

            if batch:
                inserted, updated = _upsert_books_batch(session, batch)
                stats.inserted_rows += inserted
                stats.updated_rows += updated
                batch.clear()
    finally:
        session.close()

    stats.skipped_rows = stats.total_rows - stats.processed_rows - stats.error_rows
    return stats
