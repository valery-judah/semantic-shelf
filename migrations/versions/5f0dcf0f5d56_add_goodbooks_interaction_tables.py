"""add goodbooks interaction tables

Revision ID: 5f0dcf0f5d56
Revises: 7e31874df2f4
Create Date: 2026-02-24 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5f0dcf0f5d56"
down_revision: str | Sequence[str] | None = "7e31874df2f4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "ratings",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("book_id", sa.String(length=36), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.CheckConstraint("rating BETWEEN 1 AND 5", name="ck_ratings_rating_1_5"),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "book_id"),
    )
    op.create_index("ix_ratings_book_id", "ratings", ["book_id"], unique=False)

    op.create_table(
        "tags",
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.Column("tag_name", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("tag_id"),
    )

    op.create_table(
        "book_tags",
        sa.Column("goodreads_book_id", sa.BigInteger(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["goodreads_book_id"], ["books.goodreads_book_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.tag_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("goodreads_book_id", "tag_id"),
    )
    op.create_index("ix_book_tags_tag_id", "book_tags", ["tag_id"], unique=False)

    op.create_table(
        "to_read",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("book_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "book_id"),
    )
    op.create_index("ix_to_read_book_id", "to_read", ["book_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_to_read_book_id", table_name="to_read")
    op.drop_table("to_read")

    op.drop_index("ix_book_tags_tag_id", table_name="book_tags")
    op.drop_table("book_tags")

    op.drop_table("tags")

    op.drop_index("ix_ratings_book_id", table_name="ratings")
    op.drop_table("ratings")
