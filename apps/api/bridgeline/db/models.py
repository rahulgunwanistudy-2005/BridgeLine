"""SQLAlchemy persistence models for Bridgeline's operational data."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import JsonValue
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from bridgeline.db.base import Base

IEPApprovalState = Literal["draft", "approved"]
ObligationState = Literal["pending", "confirmed", "flagged"]
BriefState = Literal["draft", "released", "confirmed", "flagged"]
PipelineRunState = Literal["queued", "running", "needs_review", "done", "error"]
AuditActorRole = Literal["case_manager", "teacher", "provider", "system"]


class Student(Base):
    """District student identity referenced by IEP and enrollment records."""

    __tablename__ = "students"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    student_ref: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class Teacher(Base):
    """District teacher identity used for class ownership and brief authorization."""

    __tablename__ = "teachers"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    teacher_ref: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class Class(Base):
    """Instructional class owned by one teacher."""

    __tablename__ = "classes"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    class_ref: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    teacher_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("teachers.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    school_year: Mapped[str] = mapped_column(String(9), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "school_year ~ '^[0-9]{4}-[0-9]{4}$'", name="ck_classes_school_year_format"
        ),
        Index("ix_classes_teacher_id", "teacher_id"),
    )


class Enrollment(Base):
    """Student membership in a class for a specific school year."""

    __tablename__ = "enrollments"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("students.id", ondelete="RESTRICT"), nullable=False
    )
    class_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("classes.id", ondelete="RESTRICT"), nullable=False
    )
    school_year: Mapped[str] = mapped_column(String(9), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "student_id", "class_id", "school_year", name="uq_enrollments_student_class_year"
        ),
        CheckConstraint(
            "school_year ~ '^[0-9]{4}-[0-9]{4}$'", name="ck_enrollments_school_year_format"
        ),
        Index("ix_enrollments_class_id", "class_id"),
        Index("ix_enrollments_student_id", "student_id"),
    )


class PipelineRun(Base):
    """Persisted lifecycle for one resumable processing pipeline."""

    __tablename__ = "pipeline_runs"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    state: Mapped[PipelineRunState] = mapped_column(String(32), nullable=False, default="queued")
    current_stage: Mapped[str | None] = mapped_column(String(100), nullable=True)
    detail: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "state IN ('queued', 'running', 'needs_review', 'done', 'error')",
            name="ck_pipeline_runs_state",
        ),
        Index("ix_pipeline_runs_state_created", "state", "created_at"),
    )


class IEPRecord(Base):
    """Immutable extracted version within a stable, human-approved IEP lineage."""

    __tablename__ = "iep_records"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    iep_record_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    student_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("students.id", ondelete="RESTRICT"), nullable=False
    )
    pipeline_run_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("pipeline_runs.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    extraction_run_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, unique=True)
    approval_state: Mapped[IEPApprovalState] = mapped_column(
        String(16), nullable=False, default="draft"
    )
    is_current_approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    payload: Mapped[dict[str, JsonValue]] = mapped_column(JSONB, nullable=False)
    disability_category: Mapped[str] = mapped_column(String(255), nullable=False)
    school_year: Mapped[str] = mapped_column(String(9), nullable=False)
    annual_review: Mapped[date | None] = mapped_column(Date, nullable=True)
    triennial_reeval: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_progress_report: Mapped[date | None] = mapped_column(Date, nullable=True)
    extracted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("iep_record_id", "version", name="uq_iep_records_lineage_version"),
        CheckConstraint("version >= 1", name="ck_iep_records_positive_version"),
        CheckConstraint(
            "approval_state IN ('draft', 'approved')", name="ck_iep_records_approval_state"
        ),
        CheckConstraint(
            "school_year ~ '^[0-9]{4}-[0-9]{4}$'",
            name="ck_iep_records_school_year_format",
        ),
        CheckConstraint(
            "(approval_state = 'draft' AND approved_at IS NULL "
            "AND is_current_approved = false AND superseded_at IS NULL) OR "
            "(approval_state = 'approved' AND approved_at IS NOT NULL "
            "AND ((is_current_approved = true AND superseded_at IS NULL) OR "
            "(is_current_approved = false AND superseded_at IS NOT NULL)))",
            name="ck_iep_records_approval_lifecycle",
        ),
        Index("ix_iep_records_student_id", "student_id"),
        Index("ix_iep_records_lineage_version", "iep_record_id", "version"),
        Index("ix_iep_records_annual_review", "annual_review"),
        Index("ix_iep_records_triennial_reeval", "triennial_reeval"),
        Index(
            "uq_iep_records_current_approved",
            "iep_record_id",
            unique=True,
            postgresql_where=text("is_current_approved = true"),
        ),
    )


class Obligation(Base):
    """Teacher obligation derived from one approved IEP version."""

    __tablename__ = "obligations"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    iep_record_version_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("iep_records.id", ondelete="RESTRICT"), nullable=False
    )
    student_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("students.id", ondelete="RESTRICT"), nullable=False
    )
    teacher_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("teachers.id", ondelete="RESTRICT"), nullable=False
    )
    class_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("classes.id", ondelete="RESTRICT"), nullable=False
    )
    accommodation_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    rule_id: Mapped[str] = mapped_column(String(255), nullable=False)
    citation: Mapped[str] = mapped_column(Text, nullable=False)
    action_text: Mapped[str] = mapped_column(Text, nullable=False)
    practice_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ObligationState] = mapped_column(String(16), nullable=False, default="pending")
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    flag_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "iep_record_version_id",
            "teacher_id",
            "class_id",
            "accommodation_id",
            "rule_id",
            name="uq_obligations_derivation",
        ),
        CheckConstraint(
            "status IN ('pending', 'confirmed', 'flagged')", name="ck_obligations_status"
        ),
        CheckConstraint(
            "(status = 'confirmed' AND confirmed_at IS NOT NULL AND flag_reason IS NULL) OR "
            "(status = 'flagged' AND confirmed_at IS NULL AND flag_reason IS NOT NULL) OR "
            "(status = 'pending' AND confirmed_at IS NULL AND flag_reason IS NULL)",
            name="ck_obligations_status_details",
        ),
        Index("ix_obligations_teacher_status", "teacher_id", "status"),
        Index("ix_obligations_class_id", "class_id"),
        Index("ix_obligations_accommodation_id", "accommodation_id"),
    )


class Brief(Base):
    """Version-bound teacher brief and its delivery state."""

    __tablename__ = "briefs"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    iep_record_version_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("iep_records.id", ondelete="RESTRICT"), nullable=False
    )
    teacher_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("teachers.id", ondelete="RESTRICT"), nullable=False
    )
    class_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("classes.id", ondelete="RESTRICT"), nullable=False
    )
    rules_version: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[BriefState] = mapped_column(String(16), nullable=False, default="draft")
    payload: Mapped[dict[str, JsonValue]] = mapped_column(JSONB, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    flag_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "iep_record_version_id",
            "teacher_id",
            "class_id",
            name="uq_briefs_version_teacher_class",
        ),
        CheckConstraint(
            "status IN ('draft', 'released', 'confirmed', 'flagged')", name="ck_briefs_status"
        ),
        Index("ix_briefs_teacher_status", "teacher_id", "status"),
    )


class AuditEvent(Base):
    """Append-only event; database triggers reject every update and delete."""

    __tablename__ = "audit_events"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    event_type: Mapped[str] = mapped_column(String(255), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actor_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    actor_role: Mapped[AuditActorRole] = mapped_column(String(32), nullable=False)
    subject_type: Mapped[str] = mapped_column(String(100), nullable=False)
    subject_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[dict[str, JsonValue]] = mapped_column(JSONB, nullable=False)
    correlation_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    pipeline_run_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("pipeline_runs.id", ondelete="RESTRICT"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "actor_role IN ('case_manager', 'teacher', 'provider', 'system')",
            name="ck_audit_events_actor_role",
        ),
        Index("ix_audit_events_occurred_at", "occurred_at"),
        Index("ix_audit_events_event_type", "event_type"),
        Index("ix_audit_events_subject", "subject_type", "subject_ref"),
        Index("ix_audit_events_pipeline_run_id", "pipeline_run_id"),
    )
