"""add source-grounded scope resolution

Revision ID: c84d19a72f10
Revises: b72e590ca641
Create Date: 2026-07-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c84d19a72f10"
down_revision: str | None = "b72e590ca641"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Persist scope provenance, aliases, and per-IEP human resolutions."""

    op.add_column(
        "obligations",
        sa.Column(
            "scope_provenance",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.alter_column("obligations", "scope_provenance", server_default=None)
    op.create_table(
        "scope_reference_aliases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("school_year", sa.String(length=9), nullable=False),
        sa.Column("scope", sa.String(length=16), nullable=False),
        sa.Column("document_ref", sa.Text(), nullable=False),
        sa.Column("normalized_ref", sa.Text(), nullable=False),
        sa.Column("target_ref", sa.String(length=255), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_by_ref", sa.String(length=255), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by_ref", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("scope IN ('subject', 'context')", name="ck_scope_alias_scope"),
        sa.CheckConstraint(
            "(active = true AND revoked_at IS NULL AND revoked_by_ref IS NULL) OR "
            "(active = false AND revoked_at IS NOT NULL AND revoked_by_ref IS NOT NULL)",
            name="ck_scope_alias_lifecycle",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "school_year",
            "scope",
            "normalized_ref",
            "target_ref",
            name="uq_scope_reference_alias_target",
        ),
    )
    op.create_index(
        "ix_scope_alias_lookup",
        "scope_reference_aliases",
        ["school_year", "scope", "normalized_ref", "active"],
    )
    op.create_table(
        "scope_reference_resolutions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("iep_record_version_id", sa.Uuid(), nullable=False),
        sa.Column("accommodation_id", sa.Uuid(), nullable=False),
        sa.Column("scope", sa.String(length=16), nullable=False),
        sa.Column("document_ref", sa.Text(), nullable=False),
        sa.Column("normalized_ref", sa.Text(), nullable=False),
        sa.Column("target_ref", sa.String(length=255), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_by_ref", sa.String(length=255), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by_ref", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("scope IN ('subject', 'context')", name="ck_scope_resolution_scope"),
        sa.CheckConstraint(
            "(active = true AND revoked_at IS NULL AND revoked_by_ref IS NULL) OR "
            "(active = false AND revoked_at IS NOT NULL AND revoked_by_ref IS NOT NULL)",
            name="ck_scope_resolution_lifecycle",
        ),
        sa.ForeignKeyConstraint(["iep_record_version_id"], ["iep_records.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "iep_record_version_id",
            "accommodation_id",
            "scope",
            "normalized_ref",
            name="uq_scope_reference_resolution",
        ),
    )
    op.create_index(
        "ix_scope_resolution_version",
        "scope_reference_resolutions",
        ["iep_record_version_id", "active"],
    )
    op.drop_constraint("ck_audit_events_actor_role", "audit_events", type_="check")
    op.create_check_constraint(
        "ck_audit_events_actor_role",
        "audit_events",
        "actor_role IN ('case_manager', 'compliance_admin', 'teacher', 'provider', 'system')",
    )


def downgrade() -> None:
    """Remove scope resolution state and obligation scope provenance."""

    op.drop_constraint("ck_audit_events_actor_role", "audit_events", type_="check")
    op.create_check_constraint(
        "ck_audit_events_actor_role",
        "audit_events",
        "actor_role IN ('case_manager', 'teacher', 'provider', 'system')",
    )
    op.drop_index("ix_scope_resolution_version", table_name="scope_reference_resolutions")
    op.drop_table("scope_reference_resolutions")
    op.drop_index("ix_scope_alias_lookup", table_name="scope_reference_aliases")
    op.drop_table("scope_reference_aliases")
    op.drop_column("obligations", "scope_provenance")
