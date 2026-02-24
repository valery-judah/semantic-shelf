"""add dataset users and user fks

Revision ID: a5f7f7c1f231
Revises: 5f0dcf0f5d56
Create Date: 2026-02-24 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a5f7f7c1f231"
down_revision: str | Sequence[str] | None = "5f0dcf0f5d56"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "dataset_users",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.execute(
        """
        INSERT INTO dataset_users (user_id)
        SELECT DISTINCT user_id
        FROM (
            SELECT user_id FROM ratings
            UNION
            SELECT user_id FROM to_read
        ) AS all_users
        """
    )

    op.create_foreign_key(
        "fk_ratings_user_id_dataset_users",
        "ratings",
        "dataset_users",
        ["user_id"],
        ["user_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_to_read_user_id_dataset_users",
        "to_read",
        "dataset_users",
        ["user_id"],
        ["user_id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("fk_to_read_user_id_dataset_users", "to_read", type_="foreignkey")
    op.drop_constraint("fk_ratings_user_id_dataset_users", "ratings", type_="foreignkey")
    op.drop_table("dataset_users")
