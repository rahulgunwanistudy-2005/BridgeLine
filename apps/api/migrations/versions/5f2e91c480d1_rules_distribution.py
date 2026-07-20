"""generalize obligations and add distribution assignments

Revision ID: 5f2e91c480d1
Revises: ec24a3719c3b
Create Date: 2026-07-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "5f2e91c480d1"
down_revision: str | None = "ec24a3719c3b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add normalized assignees and truthful obligation provenance."""

    op.create_table(
        "class_staff",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("class_id", sa.Uuid(), nullable=False),
        sa.Column("teacher_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=100), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["class_id"], ["classes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["teacher_id"], ["teachers.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("class_id", "teacher_id", name="uq_class_staff_assignment"),
    )
    op.create_index("ix_class_staff_teacher_id", "class_staff", ["teacher_id"], unique=False)
    op.execute(
        """
        INSERT INTO class_staff (id, class_id, teacher_id, role, active)
        SELECT gen_random_uuid(), id, teacher_id, 'teacher-of-record', true FROM classes
        ON CONFLICT (class_id, teacher_id) DO NOTHING
        """
    )

    op.create_table(
        "providers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider_ref", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_ref"),
    )
    op.create_table(
        "service_assignments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("iep_record_version_id", sa.Uuid(), nullable=False),
        sa.Column("service_id", sa.Uuid(), nullable=False),
        sa.Column("provider_id", sa.Uuid(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["iep_record_version_id"], ["iep_records.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["provider_id"], ["providers.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "iep_record_version_id",
            "service_id",
            "provider_id",
            name="uq_service_assignments_provider",
        ),
    )
    op.create_index(
        "ix_service_assignments_service",
        "service_assignments",
        ["iep_record_version_id", "service_id"],
        unique=False,
    )

    op.add_column("obligations", sa.Column("assignee_kind", sa.String(length=16), nullable=True))
    op.add_column("obligations", sa.Column("assignee_ref", sa.String(length=255), nullable=True))
    op.add_column("obligations", sa.Column("assignee_role", sa.String(length=255), nullable=True))
    op.add_column("obligations", sa.Column("context_kind", sa.String(length=16), nullable=True))
    op.add_column("obligations", sa.Column("context_ref", sa.String(length=255), nullable=True))
    op.add_column("obligations", sa.Column("subject", sa.String(length=255), nullable=True))
    op.add_column("obligations", sa.Column("source_kind", sa.String(length=32), nullable=True))
    op.add_column("obligations", sa.Column("source_ref", sa.Uuid(), nullable=True))
    op.execute(
        """
        UPDATE obligations AS o
        SET assignee_kind = 'teacher', assignee_ref = t.teacher_ref,
            assignee_role = 'teacher-of-record', context_kind = 'class',
            context_ref = c.class_ref, subject = c.subject,
            source_kind = 'accommodation', source_ref = o.accommodation_id
        FROM teachers AS t, classes AS c
        WHERE o.teacher_id = t.id AND o.class_id = c.id
        """
    )
    for column in (
        "assignee_kind",
        "assignee_ref",
        "assignee_role",
        "context_kind",
        "context_ref",
        "source_kind",
        "source_ref",
    ):
        op.alter_column("obligations", column, nullable=False)
    op.drop_constraint("uq_obligations_derivation", "obligations", type_="unique")
    op.drop_constraint("obligations_teacher_id_fkey", "obligations", type_="foreignkey")
    op.drop_constraint("obligations_class_id_fkey", "obligations", type_="foreignkey")
    op.drop_index("ix_obligations_teacher_status", table_name="obligations")
    op.drop_index("ix_obligations_class_id", table_name="obligations")
    op.drop_index("ix_obligations_accommodation_id", table_name="obligations")
    op.drop_column("obligations", "teacher_id")
    op.drop_column("obligations", "class_id")
    op.drop_column("obligations", "accommodation_id")
    op.create_check_constraint(
        "ck_obligations_assignee_kind", "obligations", "assignee_kind IN ('teacher', 'provider')"
    )
    op.create_check_constraint(
        "ck_obligations_context_kind",
        "obligations",
        "context_kind IN ('student', 'class', 'service')",
    )
    op.create_check_constraint(
        "ck_obligations_source_kind",
        "obligations",
        "source_kind IN ('iep_record', 'accommodation', 'service')",
    )
    op.create_unique_constraint(
        "uq_obligations_derivation",
        "obligations",
        [
            "iep_record_version_id",
            "assignee_kind",
            "assignee_ref",
            "context_kind",
            "context_ref",
            "source_kind",
            "source_ref",
            "rule_id",
        ],
    )
    op.create_index(
        "ix_obligations_assignee_status",
        "obligations",
        ["assignee_kind", "assignee_ref", "status"],
        unique=False,
    )
    op.create_index(
        "ix_obligations_context", "obligations", ["context_kind", "context_ref"], unique=False
    )
    op.create_index(
        "ix_obligations_source", "obligations", ["source_kind", "source_ref"], unique=False
    )

    op.create_table(
        "findings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("iep_record_version_id", sa.Uuid(), nullable=True),
        sa.Column("student_ref", sa.String(length=255), nullable=False),
        sa.Column("rule_id", sa.String(length=255), nullable=False),
        sa.Column("citation", sa.Text(), nullable=False),
        sa.Column("finding_type", sa.String(length=100), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("detected_on", sa.Date(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("related_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("measurements", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("status IN ('open', 'resolved')", name="ck_findings_status"),
        sa.ForeignKeyConstraint(["iep_record_version_id"], ["iep_records.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_findings_status_detected", "findings", ["status", "detected_on"], unique=False
    )
    op.create_index("ix_findings_student_ref", "findings", ["student_ref"], unique=False)


def downgrade() -> None:
    """Remove distribution assignments and restore teacher/class obligations."""

    op.drop_index("ix_findings_student_ref", table_name="findings")
    op.drop_index("ix_findings_status_detected", table_name="findings")
    op.drop_table("findings")
    op.add_column("obligations", sa.Column("teacher_id", sa.Uuid(), nullable=True))
    op.add_column("obligations", sa.Column("class_id", sa.Uuid(), nullable=True))
    op.add_column("obligations", sa.Column("accommodation_id", sa.Uuid(), nullable=True))
    op.execute(
        """
        DELETE FROM obligations
        WHERE assignee_kind <> 'teacher'
           OR context_kind <> 'class'
           OR source_kind <> 'accommodation'
        """
    )
    op.execute(
        """
        UPDATE obligations AS o
        SET teacher_id = t.id, class_id = c.id, accommodation_id = o.source_ref
        FROM teachers AS t, classes AS c
        WHERE o.assignee_ref = t.teacher_ref AND o.context_ref = c.class_ref
        """
    )
    for column in ("teacher_id", "class_id", "accommodation_id"):
        op.alter_column("obligations", column, nullable=False)
    op.drop_constraint("uq_obligations_derivation", "obligations", type_="unique")
    op.drop_constraint("ck_obligations_assignee_kind", "obligations", type_="check")
    op.drop_constraint("ck_obligations_context_kind", "obligations", type_="check")
    op.drop_constraint("ck_obligations_source_kind", "obligations", type_="check")
    op.drop_index("ix_obligations_assignee_status", table_name="obligations")
    op.drop_index("ix_obligations_context", table_name="obligations")
    op.drop_index("ix_obligations_source", table_name="obligations")
    for column in (
        "source_ref",
        "source_kind",
        "subject",
        "context_ref",
        "context_kind",
        "assignee_role",
        "assignee_ref",
        "assignee_kind",
    ):
        op.drop_column("obligations", column)
    op.create_foreign_key(
        "obligations_teacher_id_fkey",
        "obligations",
        "teachers",
        ["teacher_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "obligations_class_id_fkey",
        "obligations",
        "classes",
        ["class_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint(
        "uq_obligations_derivation",
        "obligations",
        ["iep_record_version_id", "teacher_id", "class_id", "accommodation_id", "rule_id"],
    )
    op.create_index(
        "ix_obligations_teacher_status", "obligations", ["teacher_id", "status"], unique=False
    )
    op.create_index("ix_obligations_class_id", "obligations", ["class_id"], unique=False)
    op.create_index(
        "ix_obligations_accommodation_id", "obligations", ["accommodation_id"], unique=False
    )
    op.drop_index("ix_service_assignments_service", table_name="service_assignments")
    op.drop_table("service_assignments")
    op.drop_table("providers")
    op.drop_index("ix_class_staff_teacher_id", table_name="class_staff")
    op.drop_table("class_staff")
