from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from books_rec_api.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    external_idp_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    domain_preferences: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    __table_args__ = (CheckConstraint("id LIKE 'usr_%'", name="ck_users_id_format"),)


class Book(Base):
    __tablename__ = "books"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)

    authors: Mapped[list[str]] = mapped_column(JSON, default=list)
    genres: Mapped[list[str]] = mapped_column(JSON, default=list)

    publication_year: Mapped[int | None] = mapped_column(Integer, nullable=True)

    source: Mapped[str] = mapped_column(
        Text, nullable=False, default="goodbooks", server_default=text("'goodbooks'")
    )
    goodreads_book_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, unique=True, index=True
    )
    best_book_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    work_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    books_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    isbn: Mapped[str | None] = mapped_column(Text, nullable=True)
    isbn13: Mapped[str | None] = mapped_column(Text, nullable=True)
    language_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    average_rating: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)
    ratings_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    work_ratings_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    work_text_reviews_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ratings_1: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ratings_2: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ratings_3: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ratings_4: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ratings_5: Mapped[int | None] = mapped_column(Integer, nullable=True)
    original_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    pages: Mapped[int | None] = mapped_column(Integer, nullable=True)
    publish_date_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    small_image_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class DatasetUser(Base):
    __tablename__ = "dataset_users"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)


class Rating(Base):
    __tablename__ = "ratings"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("dataset_users.user_id", ondelete="CASCADE"), primary_key=True
    )
    book_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("books.id", ondelete="CASCADE"), primary_key=True
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (CheckConstraint("rating BETWEEN 1 AND 5", name="ck_ratings_rating_1_5"),)


class Tag(Base):
    __tablename__ = "tags"

    tag_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tag_name: Mapped[str] = mapped_column(Text, nullable=False)


class BookTag(Base):
    __tablename__ = "book_tags"

    goodreads_book_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("books.goodreads_book_id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tags.tag_id", ondelete="CASCADE"), primary_key=True
    )
    count: Mapped[int] = mapped_column(Integer, nullable=False)


class ToRead(Base):
    __tablename__ = "to_read"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("dataset_users.user_id", ondelete="CASCADE"), primary_key=True
    )
    book_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("books.id", ondelete="CASCADE"), primary_key=True
    )


class BookSimilarity(Base):
    __tablename__ = "book_similarities"

    book_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("books.id", ondelete="CASCADE"), primary_key=True
    )
    neighbor_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    recs_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    algo_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class BookPopularity(Base):
    __tablename__ = "book_popularity"

    scope: Mapped[str] = mapped_column(Text, primary_key=True)
    book_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    recs_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    __table_args__ = (CheckConstraint("scope IN ('global')", name="ck_book_popularity_scope"),)


class TelemetryEvent(Base):
    __tablename__ = "telemetry_events"

    # identity
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telemetry_schema_version: Mapped[str] = mapped_column(Text, nullable=False)

    # attribution
    run_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    request_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    surface: Mapped[str] = mapped_column(Text, nullable=False)
    arm: Mapped[str] = mapped_column(Text, nullable=False)
    event_name: Mapped[str] = mapped_column(Text, nullable=False)
    is_synthetic: Mapped[bool] = mapped_column(nullable=False)

    # event time
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # content
    anchor_book_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    shown_book_ids: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    positions: Mapped[list[int] | None] = mapped_column(JSON, nullable=True)
    clicked_book_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    position: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # dedupe
    idempotency_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)

    # ingest metadata
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    __table_args__ = (Index("idx_telemetry_events_run_event", "run_id", "event_name"),)
