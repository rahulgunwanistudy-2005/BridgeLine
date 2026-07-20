"""add normalized service delivery logs

Revision ID: 9c31f4d82a07
Revises: 7a14c918b2e6
Create Date: 2026-07-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "9c31f4d82a07"
down_revision: str | None = "7a14c918b2e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Store ordinary, substitute, and explicitly targeted make-up delivery."""

    op.create_table(
        "service_delivery_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("iep_record_version_id", sa.Uuid(), nullable=False),
        sa.Column("service_id", sa.Uuid(), nullable=False),
        sa.Column("delivered_on", sa.Date(), nullable=False),
        sa.Column("minutes", sa.Integer(), nullable=False),
        sa.Column("provider_ref", sa.String(length=255), nullable=False),
        sa.Column("substitute_for_ref", sa.String(length=255), nullable=True),
        sa.Column("makeup_for_week_start", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("minutes > 0", name="ck_service_delivery_logs_positive_minutes"),
        sa.CheckConstraint(
            "makeup_for_week_start IS NULL OR EXTRACT(ISODOW FROM makeup_for_week_start) = 1",
            name="ck_service_delivery_logs_makeup_monday",
        ),
        sa.ForeignKeyConstraint(["iep_record_version_id"], ["iep_records.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_service_delivery_logs_service_date",
        "service_delivery_logs",
        ["iep_record_version_id", "service_id", "delivered_on"],
        unique=False,
    )
    op.create_index(
        "ix_service_delivery_logs_makeup_week",
        "service_delivery_logs",
        ["makeup_for_week_start"],
        unique=False,
    )


def downgrade() -> None:
    """Remove service delivery facts."""

    op.drop_index("ix_service_delivery_logs_makeup_week", table_name="service_delivery_logs")
    op.drop_index("ix_service_delivery_logs_service_date", table_name="service_delivery_logs")
    op.drop_table("service_delivery_logs")
