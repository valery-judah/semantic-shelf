from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import select, text, tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from books_rec_api.database import SessionLocal
from books_rec_api.models import BookTag, DatasetUser, Rating, Tag, ToRead


@dataclass
class TableImportStats:
    total_rows: int = 0
    inserted_rows: int = 0
    updated_rows: int = 0
    error_rows: int = 0


@dataclass
class InteractionsImportStats:
    dataset_users: TableImportStats
    ratings: TableImportStats
    tags: TableImportStats
    book_tags: TableImportStats
    to_read: TableImportStats


def _parse_required_int(value: str | None, *, field: str) -> int:
    if value is None or value.strip() == "":
        raise ValueError(f"{field} is required")
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"Invalid integer for {field}: {value!r}") from exc


def map_rating_row(row: dict[str, str]) -> dict[str, Any]:
    return {
        "user_id": _parse_required_int(row.get("user_id"), field="user_id"),
        "book_id": str(_parse_required_int(row.get("book_id"), field="book_id")),
        "rating": _parse_required_int(row.get("rating"), field="rating"),
    }


def map_tag_row(row: dict[str, str]) -> dict[str, Any]:
    tag_id = _parse_required_int(row.get("tag_id"), field="tag_id")
    name = (row.get("tag_name") or "").strip()
    if not name:
        raise ValueError("tag_name is required")
    return {"tag_id": tag_id, "tag_name": name}


def map_book_tag_row(row: dict[str, str]) -> dict[str, Any]:
    return {
        "goodreads_book_id": _parse_required_int(
            row.get("goodreads_book_id"), field="goodreads_book_id"
        ),
        "tag_id": _parse_required_int(row.get("tag_id"), field="tag_id"),
        "count": _parse_required_int(row.get("count"), field="count"),
    }


def map_to_read_row(row: dict[str, str]) -> dict[str, Any]:
    return {
        "user_id": _parse_required_int(row.get("user_id"), field="user_id"),
        "book_id": str(_parse_required_int(row.get("book_id"), field="book_id")),
    }


def map_dataset_user_row(row: dict[str, str]) -> dict[str, Any]:
    return {"user_id": _parse_required_int(row.get("user_id"), field="user_id")}


def _import_dataset_users(
    session: Session,
    *,
    ratings_path: Path,
    to_read_path: Path,
    batch_size: int,
    max_error_logs: int,
) -> TableImportStats:
    stats = TableImportStats()
    user_ids: set[int] = set()

    for path in [ratings_path, to_read_path]:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row_num, row in enumerate(reader, start=2):
                stats.total_rows += 1
                try:
                    mapped = map_dataset_user_row(row)
                except ValueError as exc:
                    stats.error_rows += 1
                    if stats.error_rows <= max_error_logs:
                        print(f"[{path.name}:{row_num}] parse error: {exc}")
                    continue
                user_ids.add(mapped["user_id"])

    rows = [{"user_id": user_id} for user_id in sorted(user_ids)]
    for start in range(0, len(rows), batch_size):
        inserted, updated = _insert_batches(
            session,
            rows[start : start + batch_size],
            model=DatasetUser,
            conflict_columns=["user_id"],
            update_columns=[],
        )
        stats.inserted_rows += inserted
        stats.updated_rows += updated

    return stats


def _insert_batches(
    session: Session,
    rows: list[dict[str, Any]],
    *,
    model: type[Any],
    conflict_columns: list[str],
    update_columns: list[str],
) -> tuple[int, int]:
    if not rows:
        return 0, 0

    deduped: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in rows:
        deduped[tuple(row[column] for column in conflict_columns)] = row
    rows_to_write = list(deduped.values())

    conflict_attrs = [getattr(model, column) for column in conflict_columns]
    key_tuples = [tuple(row[column] for column in conflict_columns) for row in rows_to_write]
    existing_rows = session.execute(
        select(*conflict_attrs).where(tuple_(*conflict_attrs).in_(key_tuples))
    ).all()
    existing = len(existing_rows)

    stmt = insert(model).values(rows_to_write)
    if update_columns:
        stmt = stmt.on_conflict_do_update(
            index_elements=conflict_columns,
            set_={column: getattr(stmt.excluded, column) for column in update_columns},
        )
    else:
        stmt = stmt.on_conflict_do_nothing(index_elements=conflict_columns)

    session.execute(stmt)
    inserted = len(rows_to_write) - existing
    updated = existing if update_columns else 0
    return inserted, updated


def _import_csv(
    session: Session,
    *,
    path: Path,
    mapper: Any,
    model: type[Any],
    conflict_columns: list[str],
    update_columns: list[str],
    batch_size: int,
    max_error_logs: int,
) -> TableImportStats:
    stats = TableImportStats()
    batch: list[dict[str, Any]] = []

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row_num, row in enumerate(reader, start=2):
            stats.total_rows += 1
            try:
                batch.append(mapper(row))
            except ValueError as exc:
                stats.error_rows += 1
                if stats.error_rows <= max_error_logs:
                    print(f"[{path.name}:{row_num}] parse error: {exc}")
                continue

            if len(batch) >= batch_size:
                inserted, updated = _insert_batches(
                    session,
                    batch,
                    model=model,
                    conflict_columns=conflict_columns,
                    update_columns=update_columns,
                )
                stats.inserted_rows += inserted
                stats.updated_rows += updated
                batch.clear()

    if batch:
        inserted, updated = _insert_batches(
            session,
            batch,
            model=model,
            conflict_columns=conflict_columns,
            update_columns=update_columns,
        )
        stats.inserted_rows += inserted
        stats.updated_rows += updated
        batch.clear()

    return stats


def import_interactions(
    data_dir: Path | str,
    *,
    use_samples: bool = False,
    truncate_tables: bool = False,
    batch_size: int = 5000,
    max_error_logs: int = 20,
) -> InteractionsImportStats:
    data_path = Path(data_dir)
    base_path = data_path / "samples" if use_samples else data_path

    ratings_path = base_path / "ratings.csv"
    tags_path = base_path / "tags.csv"
    book_tags_path = base_path / "book_tags.csv"
    to_read_path = base_path / "to_read.csv"

    for path in [ratings_path, tags_path, book_tags_path, to_read_path]:
        if not path.exists():
            raise FileNotFoundError(f"Required CSV not found: {path}")
    if batch_size < 1:
        raise ValueError("batch_size must be >= 1")

    session = SessionLocal()
    try:
        with session.begin():
            if truncate_tables:
                session.execute(
                    text("TRUNCATE TABLE ratings, book_tags, tags, to_read, dataset_users")
                )

            dataset_users_stats = _import_dataset_users(
                session,
                ratings_path=ratings_path,
                to_read_path=to_read_path,
                batch_size=batch_size,
                max_error_logs=max_error_logs,
            )

            tags_stats = _import_csv(
                session,
                path=tags_path,
                mapper=map_tag_row,
                model=Tag,
                conflict_columns=["tag_id"],
                update_columns=["tag_name"],
                batch_size=batch_size,
                max_error_logs=max_error_logs,
            )
            ratings_stats = _import_csv(
                session,
                path=ratings_path,
                mapper=map_rating_row,
                model=Rating,
                conflict_columns=["user_id", "book_id"],
                update_columns=["rating"],
                batch_size=batch_size,
                max_error_logs=max_error_logs,
            )
            to_read_stats = _import_csv(
                session,
                path=to_read_path,
                mapper=map_to_read_row,
                model=ToRead,
                conflict_columns=["user_id", "book_id"],
                update_columns=[],
                batch_size=batch_size,
                max_error_logs=max_error_logs,
            )
            book_tags_stats = _import_csv(
                session,
                path=book_tags_path,
                mapper=map_book_tag_row,
                model=BookTag,
                conflict_columns=["goodreads_book_id", "tag_id"],
                update_columns=["count"],
                batch_size=batch_size,
                max_error_logs=max_error_logs,
            )
    finally:
        session.close()

    return InteractionsImportStats(
        dataset_users=dataset_users_stats,
        ratings=ratings_stats,
        tags=tags_stats,
        book_tags=book_tags_stats,
        to_read=to_read_stats,
    )
