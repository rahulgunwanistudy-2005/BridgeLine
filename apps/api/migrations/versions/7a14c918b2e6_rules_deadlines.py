"""add school calendar and compliance deadlines

Revision ID: 7a14c918b2e6
Revises: 5f2e91c480d1
Create Date: 2026-07-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7a14c918b2e6"
down_revision: str | None = "5f2e91c480d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create normalized calendar inputs and derived deadline storage."""

    op.create_table(
        "school_calendar_days",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("school_year", sa.String(length=9), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("instructional", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "school_year ~ '^[0-9]{4}-[0-9]{4}$'",
            name="ck_school_calendar_days_year_format",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("school_year", "day", name="uq_school_calendar_day"),
    )
    op.create_index(
        "ix_school_calendar_days_year_day",
        "school_calendar_days",
        ["school_year", "day"],
        unique=False,
    )
    op.create_table(
        "school_terms",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("term_ref", sa.String(length=255), nullable=False),
        sa.Column("school_year", sa.String(length=9), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("start_on", sa.Date(), nullable=False),
        sa.Column("end_on", sa.Date(), nullable=False),
        sa.CheckConstraint("kind IN ('semester', 'grading_period')", name="ck_school_terms_kind"),
        sa.CheckConstraint("end_on >= start_on", name="ck_school_terms_date_order"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("term_ref"),
    )
    op.create_index(
        "ix_school_terms_year_kind", "school_terms", ["school_year", "kind"], unique=False
    )
    op.create_table(
        "student_compliance_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("school_year", sa.String(length=9), nullable=False),
        sa.Column("initial_eligibility", sa.Boolean(), nullable=False),
        sa.Column("eligibility_determined_on", sa.Date(), nullable=True),
        sa.CheckConstraint(
            "initial_eligibility = true OR eligibility_determined_on IS NULL",
            name="ck_compliance_profile_eligibility_date",
        ),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id", "school_year", name="uq_student_compliance_profile"),
    )
    op.create_index(
        "ix_student_compliance_profiles_year",
        "student_compliance_profiles",
        ["school_year"],
        unique=False,
    )
    op.create_table(
        "compliance_deadlines",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("iep_record_version_id", sa.Uuid(), nullable=False),
        sa.Column("student_ref", sa.String(length=255), nullable=False),
        sa.Column("rule_id", sa.String(length=255), nullable=False),
        sa.Column("citation", sa.Text(), nullable=False),
        sa.Column("source_kind", sa.String(length=32), nullable=False),
        sa.Column("source_ref", sa.Uuid(), nullable=False),
        sa.Column("legal_due_on", sa.Date(), nullable=False),
        sa.Column("action_due_on", sa.Date(), nullable=False),
        sa.Column("warning_30_on", sa.Date(), nullable=False),
        sa.Column("warning_14_on", sa.Date(), nullable=False),
        sa.Column("warning_3_on", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('upcoming', 'due', 'overdue')",
            name="ck_compliance_deadlines_status",
        ),
        sa.ForeignKeyConstraint(["iep_record_version_id"], ["iep_records.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "iep_record_version_id",
            "rule_id",
            "source_kind",
            "source_ref",
            name="uq_compliance_deadline_derivation",
        ),
    )
    op.create_index(
        "ix_compliance_deadlines_status_due",
        "compliance_deadlines",
        ["status", "legal_due_on"],
        unique=False,
    )
    op.create_index(
        "ix_compliance_deadlines_student_ref",
        "compliance_deadlines",
        ["student_ref"],
        unique=False,
    )


def downgrade() -> None:
    """Remove derived deadlines and their normalized source facts."""

    op.drop_index("ix_compliance_deadlines_student_ref", table_name="compliance_deadlines")
    op.drop_index("ix_compliance_deadlines_status_due", table_name="compliance_deadlines")
    op.drop_table("compliance_deadlines")
    op.drop_index("ix_student_compliance_profiles_year", table_name="student_compliance_profiles")
    op.drop_table("student_compliance_profiles")
    op.drop_index("ix_school_terms_year_kind", table_name="school_terms")
    op.drop_table("school_terms")
    op.drop_index("ix_school_calendar_days_year_day", table_name="school_calendar_days")
    op.drop_table("school_calendar_days")
