"""extend books with goodbooks metadata

Revision ID: 7e31874df2f4
Revises: 9b8446d4f144
Create Date: 2026-02-24 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7e31874df2f4"
down_revision: str | Sequence[str] | None = "9b8446d4f144"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "books",
        sa.Column("source", sa.Text(), nullable=False, server_default=sa.text("'goodbooks'")),
    )
    op.add_column("books", sa.Column("goodreads_book_id", sa.BigInteger(), nullable=True))
    op.add_column("books", sa.Column("best_book_id", sa.BigInteger(), nullable=True))
    op.add_column("books", sa.Column("work_id", sa.BigInteger(), nullable=True))
    op.add_column("books", sa.Column("books_count", sa.Integer(), nullable=True))
    op.add_column("books", sa.Column("isbn", sa.Text(), nullable=True))
    op.add_column("books", sa.Column("isbn13", sa.Text(), nullable=True))
    op.add_column("books", sa.Column("language_code", sa.Text(), nullable=True))
    op.add_column(
        "books", sa.Column("average_rating", sa.Numeric(precision=3, scale=2), nullable=True)
    )
    op.add_column("books", sa.Column("ratings_count", sa.Integer(), nullable=True))
    op.add_column("books", sa.Column("work_ratings_count", sa.Integer(), nullable=True))
    op.add_column("books", sa.Column("work_text_reviews_count", sa.Integer(), nullable=True))
    op.add_column("books", sa.Column("ratings_1", sa.Integer(), nullable=True))
    op.add_column("books", sa.Column("ratings_2", sa.Integer(), nullable=True))
    op.add_column("books", sa.Column("ratings_3", sa.Integer(), nullable=True))
    op.add_column("books", sa.Column("ratings_4", sa.Integer(), nullable=True))
    op.add_column("books", sa.Column("ratings_5", sa.Integer(), nullable=True))
    op.add_column("books", sa.Column("original_title", sa.Text(), nullable=True))
    op.add_column("books", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("books", sa.Column("pages", sa.Integer(), nullable=True))
    op.add_column("books", sa.Column("publish_date_raw", sa.Text(), nullable=True))
    op.add_column("books", sa.Column("image_url", sa.Text(), nullable=True))
    op.add_column("books", sa.Column("small_image_url", sa.Text(), nullable=True))

    op.create_index("ix_books_goodreads_book_id", "books", ["goodreads_book_id"], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_books_goodreads_book_id", table_name="books")

    op.drop_column("books", "small_image_url")
    op.drop_column("books", "image_url")
    op.drop_column("books", "publish_date_raw")
    op.drop_column("books", "pages")
    op.drop_column("books", "description")
    op.drop_column("books", "original_title")
    op.drop_column("books", "ratings_5")
    op.drop_column("books", "ratings_4")
    op.drop_column("books", "ratings_3")
    op.drop_column("books", "ratings_2")
    op.drop_column("books", "ratings_1")
    op.drop_column("books", "work_text_reviews_count")
    op.drop_column("books", "work_ratings_count")
    op.drop_column("books", "ratings_count")
    op.drop_column("books", "average_rating")
    op.drop_column("books", "language_code")
    op.drop_column("books", "isbn13")
    op.drop_column("books", "isbn")
    op.drop_column("books", "books_count")
    op.drop_column("books", "work_id")
    op.drop_column("books", "best_book_id")
    op.drop_column("books", "goodreads_book_id")
    op.drop_column("books", "source")
