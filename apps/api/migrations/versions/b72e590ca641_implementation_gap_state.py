"""add implementation gap operational state

Revision ID: b72e590ca641
Revises: 9c31f4d82a07
Create Date: 2026-07-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b72e590ca641"
down_revision: str | None = "9c31f4d82a07"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Store documented service-delay reasons and enforce finding lifecycle state."""

    op.create_table(
        "service_delay_reasons",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("iep_record_version_id", sa.Uuid(), nullable=False),
        sa.Column("service_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_by_ref", sa.String(length=255), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by_ref", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("length(trim(reason)) > 0", name="ck_service_delay_reason_nonempty"),
        sa.CheckConstraint(
            "(active = true AND revoked_at IS NULL AND revoked_by_ref IS NULL) OR "
            "(active = false AND revoked_at IS NOT NULL AND revoked_by_ref IS NOT NULL)",
            name="ck_service_delay_reason_lifecycle",
        ),
        sa.ForeignKeyConstraint(["iep_record_version_id"], ["iep_records.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("iep_record_version_id", "service_id", name="uq_service_delay_reason"),
    )
    op.create_check_constraint(
        "ck_findings_status_details",
        "findings",
        "(status = 'open' AND resolved_at IS NULL) OR "
        "(status = 'resolved' AND resolved_at IS NOT NULL)",
    )


def downgrade() -> None:
    """Remove implementation-gap operational state."""

    op.drop_constraint("ck_findings_status_details", "findings", type_="check")
    op.drop_table("service_delay_reasons")
