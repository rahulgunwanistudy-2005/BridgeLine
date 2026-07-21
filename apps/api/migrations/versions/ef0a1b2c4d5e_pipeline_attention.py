"""add pipeline approval and attention state

Revision ID: ef0a1b2c4d5e
Revises: d39e7a3c18f2
Create Date: 2026-07-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "ef0a1b2c4d5e"
down_revision: str | None = "d39e7a3c18f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Persist why a run requires attention without overloading event state."""

    op.add_column("pipeline_runs", sa.Column("attention_kind", sa.String(length=32), nullable=True))
    op.add_column(
        "pipeline_runs",
        sa.Column("attention_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "pipeline_runs",
        sa.Column("retryable", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("pipeline_runs", "retryable", server_default=None)
    op.drop_constraint("ck_pipeline_runs_state", "pipeline_runs", type_="check")
    op.create_check_constraint(
        "ck_pipeline_runs_state",
        "pipeline_runs",
        "state IN ('queued', 'running', 'awaiting_approval', 'needs_review', 'done', 'error')",
    )
    op.create_check_constraint(
        "ck_pipeline_runs_attention_kind",
        "pipeline_runs",
        "attention_kind IS NULL OR attention_kind IN "
        "('human_approval', 'model_uncertainty', 'system_failure')",
    )


def downgrade() -> None:
    """Remove approval and attention metadata."""

    op.drop_constraint("ck_pipeline_runs_attention_kind", "pipeline_runs", type_="check")
    op.drop_constraint("ck_pipeline_runs_state", "pipeline_runs", type_="check")
    op.create_check_constraint(
        "ck_pipeline_runs_state",
        "pipeline_runs",
        "state IN ('queued', 'running', 'needs_review', 'done', 'error')",
    )
    op.drop_column("pipeline_runs", "retryable")
    op.drop_column("pipeline_runs", "attention_payload")
    op.drop_column("pipeline_runs", "attention_kind")
