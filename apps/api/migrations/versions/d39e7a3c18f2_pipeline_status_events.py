"""add durable pipeline status events

Revision ID: d39e7a3c18f2
Revises: c84d19a72f10
Create Date: 2026-07-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d39e7a3c18f2"
down_revision: str | None = "c84d19a72f10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Persist status history and serialize sequence allocation per run."""

    op.add_column(
        "pipeline_runs",
        sa.Column("next_event_seq", sa.Integer(), nullable=False, server_default="0"),
    )
    op.alter_column("pipeline_runs", "next_event_seq", server_default=None)
    op.create_table(
        "pipeline_status_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("stage", sa.String(length=100), nullable=False),
        sa.Column("agent_label", sa.String(length=255), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("progress", sa.Float(), nullable=True),
        sa.Column("parent_stage", sa.String(length=100), nullable=True),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("seq >= 1", name="ck_pipeline_status_events_positive_seq"),
        sa.CheckConstraint(
            "state IN ('queued', 'running', 'done', 'needs_review', 'error')",
            name="ck_pipeline_status_events_state",
        ),
        sa.CheckConstraint(
            "progress IS NULL OR (progress >= 0.0 AND progress <= 1.0)",
            name="ck_pipeline_status_events_progress",
        ),
        sa.ForeignKeyConstraint(["run_id"], ["pipeline_runs.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "seq", name="uq_pipeline_status_events_run_seq"),
    )
    op.create_index(
        "ix_pipeline_status_events_run_seq", "pipeline_status_events", ["run_id", "seq"]
    )


def downgrade() -> None:
    """Remove durable status history."""

    op.drop_index("ix_pipeline_status_events_run_seq", table_name="pipeline_status_events")
    op.drop_table("pipeline_status_events")
    op.drop_column("pipeline_runs", "next_event_seq")
