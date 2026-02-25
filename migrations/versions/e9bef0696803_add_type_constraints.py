"""add type constraints

Revision ID: e9bef0696803
Revises: a4e20bb1deb6
Create Date: 2026-02-25 14:23:32.271015

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e9bef0696803"
down_revision: str | Sequence[str] | None = "a4e20bb1deb6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_check_constraint(
        "ck_users_id_format",
        "users",
        "id LIKE 'usr_%'",
    )
    op.create_check_constraint(
        "ck_book_popularity_scope",
        "book_popularity",
        "scope IN ('global')",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("ck_book_popularity_scope", "book_popularity", type_="check")
    op.drop_constraint("ck_users_id_format", "users", type_="check")
