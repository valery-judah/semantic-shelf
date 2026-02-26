"""add_telemetry_events

Revision ID: f99216de62a9
Revises: e9bef0696803
Create Date: 2026-02-26 19:41:45.755172

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f99216de62a9"
down_revision: str | Sequence[str] | None = "e9bef0696803"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "telemetry_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("telemetry_schema_version", sa.Text(), nullable=False),
        sa.Column("run_id", sa.Text(), nullable=False),
        sa.Column("request_id", sa.Text(), nullable=False),
        sa.Column("surface", sa.Text(), nullable=False),
        sa.Column("arm", sa.Text(), nullable=False),
        sa.Column("event_name", sa.Text(), nullable=False),
        sa.Column("is_synthetic", sa.Boolean(), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("anchor_book_id", sa.Text(), nullable=True),
        sa.Column("shown_book_ids", sa.JSON(), nullable=True),
        sa.Column("positions", sa.JSON(), nullable=True),
        sa.Column("clicked_book_id", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=True),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index(
        "idx_telemetry_events_run_event",
        "telemetry_events",
        ["run_id", "event_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_telemetry_events_request_id"), "telemetry_events", ["request_id"], unique=False
    )
    op.create_index(
        op.f("ix_telemetry_events_run_id"), "telemetry_events", ["run_id"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_telemetry_events_run_id"), table_name="telemetry_events")
    op.drop_index(op.f("ix_telemetry_events_request_id"), table_name="telemetry_events")
    op.drop_index("idx_telemetry_events_run_event", table_name="telemetry_events")
    op.drop_table("telemetry_events")
