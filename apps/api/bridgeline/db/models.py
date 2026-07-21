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
    Float,
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
ObligationAssigneeKind = Literal["teacher", "provider"]
ObligationContextKind = Literal["student", "class", "service"]
ObligationSourceKind = Literal["iep_record", "accommodation", "service"]
FindingState = Literal["open", "resolved"]
DeadlineState = Literal["upcoming", "due", "overdue"]
SchoolTermKind = Literal["semester", "grading_period"]
BriefState = Literal["draft", "released", "confirmed", "flagged"]
PipelineRunState = Literal[
    "queued", "running", "awaiting_approval", "needs_review", "done", "error"
]
AuditActorRole = Literal["case_manager", "compliance_admin", "teacher", "provider", "system"]


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


class ClassStaff(Base):
    """A teacher-of-record assignment, including co-teachers."""

    __tablename__ = "class_staff"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    class_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("classes.id", ondelete="RESTRICT"), nullable=False
    )
    teacher_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("teachers.id", ondelete="RESTRICT"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(100), nullable=False, default="teacher-of-record")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("class_id", "teacher_id", name="uq_class_staff_assignment"),
        Index("ix_class_staff_teacher_id", "teacher_id"),
    )


class ScopeReferenceAlias(Base):
    """District-approved document phrase mapped to one roster vocabulary value."""

    __tablename__ = "scope_reference_aliases"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    school_year: Mapped[str] = mapped_column(String(9), nullable=False)
    scope: Mapped[str] = mapped_column(String(16), nullable=False)
    document_ref: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_ref: Mapped[str] = mapped_column(Text, nullable=False)
    target_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_by_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "school_year",
            "scope",
            "normalized_ref",
            "target_ref",
            name="uq_scope_reference_alias_target",
        ),
        CheckConstraint("scope IN ('subject', 'context')", name="ck_scope_alias_scope"),
        CheckConstraint(
            "(active = true AND revoked_at IS NULL AND revoked_by_ref IS NULL) OR "
            "(active = false AND revoked_at IS NOT NULL AND revoked_by_ref IS NOT NULL)",
            name="ck_scope_alias_lifecycle",
        ),
        Index("ix_scope_alias_lookup", "school_year", "scope", "normalized_ref", "active"),
    )


class ScopeReferenceResolution(Base):
    """Case-manager mapping for one approved accommodation scope reference."""

    __tablename__ = "scope_reference_resolutions"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    iep_record_version_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("iep_records.id", ondelete="RESTRICT"), nullable=False
    )
    accommodation_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    scope: Mapped[str] = mapped_column(String(16), nullable=False)
    document_ref: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_ref: Mapped[str] = mapped_column(Text, nullable=False)
    target_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_by_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "iep_record_version_id",
            "accommodation_id",
            "scope",
            "normalized_ref",
            name="uq_scope_reference_resolution",
        ),
        CheckConstraint("scope IN ('subject', 'context')", name="ck_scope_resolution_scope"),
        CheckConstraint(
            "(active = true AND revoked_at IS NULL AND revoked_by_ref IS NULL) OR "
            "(active = false AND revoked_at IS NOT NULL AND revoked_by_ref IS NOT NULL)",
            name="ck_scope_resolution_lifecycle",
        ),
        Index("ix_scope_resolution_version", "iep_record_version_id", "active"),
    )


class Provider(Base):
    """Related-service provider who may receive IEP obligations."""

    __tablename__ = "providers"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    provider_ref: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SchoolCalendarDay(Base):
    """One district school-local date used for deterministic date adjustment."""

    __tablename__ = "school_calendar_days"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    school_year: Mapped[str] = mapped_column(String(9), nullable=False)
    day: Mapped[date] = mapped_column(Date, nullable=False)
    instructional: Mapped[bool] = mapped_column(Boolean, nullable=False)

    __table_args__ = (
        UniqueConstraint("school_year", "day", name="uq_school_calendar_day"),
        CheckConstraint(
            "school_year ~ '^[0-9]{4}-[0-9]{4}$'",
            name="ck_school_calendar_days_year_format",
        ),
        Index("ix_school_calendar_days_year_day", "school_year", "day"),
    )


class SchoolTerm(Base):
    """Named semester or grading period within a school year."""

    __tablename__ = "school_terms"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    term_ref: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    school_year: Mapped[str] = mapped_column(String(9), nullable=False)
    kind: Mapped[SchoolTermKind] = mapped_column(String(32), nullable=False)
    start_on: Mapped[date] = mapped_column(Date, nullable=False)
    end_on: Mapped[date] = mapped_column(Date, nullable=False)

    __table_args__ = (
        CheckConstraint("kind IN ('semester', 'grading_period')", name="ck_school_terms_kind"),
        CheckConstraint("end_on >= start_on", name="ck_school_terms_date_order"),
        Index("ix_school_terms_year_kind", "school_year", "kind"),
    )


class StudentComplianceProfile(Base):
    """Student deadline facts outside approved existing-IEP payloads."""

    __tablename__ = "student_compliance_profiles"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("students.id", ondelete="RESTRICT"), nullable=False
    )
    school_year: Mapped[str] = mapped_column(String(9), nullable=False)
    initial_eligibility: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    eligibility_determined_on: Mapped[date | None] = mapped_column(Date, nullable=True)

    __table_args__ = (
        UniqueConstraint("student_id", "school_year", name="uq_student_compliance_profile"),
        CheckConstraint(
            "initial_eligibility = true OR eligibility_determined_on IS NULL",
            name="ck_compliance_profile_eligibility_date",
        ),
        Index("ix_student_compliance_profiles_year", "school_year"),
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
    next_event_seq: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    attention_kind: Mapped[str | None] = mapped_column(String(32), nullable=True)
    attention_payload: Mapped[dict[str, JsonValue] | None] = mapped_column(JSONB, nullable=True)
    retryable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
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
            "state IN ('queued', 'running', 'awaiting_approval', 'needs_review', 'done', 'error')",
            name="ck_pipeline_runs_state",
        ),
        Index("ix_pipeline_runs_state_created", "state", "created_at"),
    )


class PipelineStatusEvent(Base):
    """One append-only, resumable status event for a pipeline run."""

    __tablename__ = "pipeline_status_events"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("pipeline_runs.id", ondelete="RESTRICT"), nullable=False
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    stage: Mapped[str] = mapped_column(String(100), nullable=False)
    agent_label: Mapped[str] = mapped_column(String(255), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False)
    progress: Mapped[float | None] = mapped_column(Float, nullable=True)
    parent_stage: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint("seq >= 1", name="ck_pipeline_status_events_positive_seq"),
        CheckConstraint(
            "state IN ('queued', 'running', 'done', 'needs_review', 'error')",
            name="ck_pipeline_status_events_state",
        ),
        CheckConstraint(
            "progress IS NULL OR (progress >= 0.0 AND progress <= 1.0)",
            name="ck_pipeline_status_events_progress",
        ),
        UniqueConstraint("run_id", "seq", name="uq_pipeline_status_events_run_seq"),
        Index("ix_pipeline_status_events_run_seq", "run_id", "seq"),
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
    """Assignee obligation derived from one approved IEP version."""

    __tablename__ = "obligations"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    iep_record_version_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("iep_records.id", ondelete="RESTRICT"), nullable=False
    )
    student_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("students.id", ondelete="RESTRICT"), nullable=False
    )
    assignee_kind: Mapped[ObligationAssigneeKind] = mapped_column(String(16), nullable=False)
    assignee_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    assignee_role: Mapped[str] = mapped_column(String(255), nullable=False)
    context_kind: Mapped[ObligationContextKind] = mapped_column(String(16), nullable=False)
    context_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_kind: Mapped[ObligationSourceKind] = mapped_column(String(32), nullable=False)
    source_ref: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    scope_provenance: Mapped[list[dict[str, JsonValue]]] = mapped_column(
        JSONB, nullable=False, default=list
    )
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
            "assignee_kind",
            "assignee_ref",
            "context_kind",
            "context_ref",
            "source_kind",
            "source_ref",
            "rule_id",
            name="uq_obligations_derivation",
        ),
        CheckConstraint(
            "assignee_kind IN ('teacher', 'provider')", name="ck_obligations_assignee_kind"
        ),
        CheckConstraint(
            "context_kind IN ('student', 'class', 'service')",
            name="ck_obligations_context_kind",
        ),
        CheckConstraint(
            "source_kind IN ('iep_record', 'accommodation', 'service')",
            name="ck_obligations_source_kind",
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
        Index("ix_obligations_assignee_status", "assignee_kind", "assignee_ref", "status"),
        Index("ix_obligations_context", "context_kind", "context_ref"),
        Index("ix_obligations_source", "source_kind", "source_ref"),
    )


class ServiceAssignment(Base):
    """Provider-of-record assignment for a service in one approved IEP version."""

    __tablename__ = "service_assignments"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    iep_record_version_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("iep_records.id", ondelete="RESTRICT"), nullable=False
    )
    service_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    provider_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("providers.id", ondelete="RESTRICT"), nullable=False
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "iep_record_version_id",
            "service_id",
            "provider_id",
            name="uq_service_assignments_provider",
        ),
        Index("ix_service_assignments_service", "iep_record_version_id", "service_id"),
    )


class ServiceDeliveryLog(Base):
    """Immutable record of delivered service minutes or targeted make-up minutes."""

    __tablename__ = "service_delivery_logs"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    iep_record_version_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("iep_records.id", ondelete="RESTRICT"), nullable=False
    )
    service_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    delivered_on: Mapped[date] = mapped_column(Date, nullable=False)
    minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    provider_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    substitute_for_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    makeup_for_week_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("minutes > 0", name="ck_service_delivery_logs_positive_minutes"),
        CheckConstraint(
            "makeup_for_week_start IS NULL OR EXTRACT(ISODOW FROM makeup_for_week_start) = 1",
            name="ck_service_delivery_logs_makeup_monday",
        ),
        Index(
            "ix_service_delivery_logs_service_date",
            "iep_record_version_id",
            "service_id",
            "delivered_on",
        ),
        Index("ix_service_delivery_logs_makeup_week", "makeup_for_week_start"),
    )


class ServiceDelayReason(Base):
    """Documented reason that suppresses the operational service-start lag check."""

    __tablename__ = "service_delay_reasons"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    iep_record_version_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("iep_records.id", ondelete="RESTRICT"), nullable=False
    )
    service_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_by_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_by_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("iep_record_version_id", "service_id", name="uq_service_delay_reason"),
        CheckConstraint("length(trim(reason)) > 0", name="ck_service_delay_reason_nonempty"),
        CheckConstraint(
            "(active = true AND revoked_at IS NULL AND revoked_by_ref IS NULL) OR "
            "(active = false AND revoked_at IS NOT NULL AND revoked_by_ref IS NOT NULL)",
            name="ck_service_delay_reason_lifecycle",
        ),
    )


class Finding(Base):
    """Deterministic compliance finding tied to a cited registered rule."""

    __tablename__ = "findings"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    iep_record_version_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("iep_records.id", ondelete="RESTRICT"), nullable=True
    )
    student_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    rule_id: Mapped[str] = mapped_column(String(255), nullable=False)
    citation: Mapped[str] = mapped_column(Text, nullable=False)
    finding_type: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    detected_on: Mapped[date] = mapped_column(Date, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False)
    related_refs: Mapped[dict[str, JsonValue]] = mapped_column(JSONB, nullable=False)
    measurements: Mapped[dict[str, JsonValue]] = mapped_column(JSONB, nullable=False)
    status: Mapped[FindingState] = mapped_column(String(16), nullable=False, default="open")
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("status IN ('open', 'resolved')", name="ck_findings_status"),
        CheckConstraint(
            "(status = 'open' AND resolved_at IS NULL) OR "
            "(status = 'resolved' AND resolved_at IS NOT NULL)",
            name="ck_findings_status_details",
        ),
        Index("ix_findings_status_detected", "status", "detected_on"),
        Index("ix_findings_student_ref", "student_ref"),
    )


class ComplianceDeadline(Base):
    """Persisted cited deadline derived from one approved IEP version."""

    __tablename__ = "compliance_deadlines"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    iep_record_version_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("iep_records.id", ondelete="RESTRICT"), nullable=False
    )
    student_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    rule_id: Mapped[str] = mapped_column(String(255), nullable=False)
    citation: Mapped[str] = mapped_column(Text, nullable=False)
    source_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    source_ref: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    legal_due_on: Mapped[date] = mapped_column(Date, nullable=False)
    action_due_on: Mapped[date] = mapped_column(Date, nullable=False)
    warning_30_on: Mapped[date] = mapped_column(Date, nullable=False)
    warning_14_on: Mapped[date] = mapped_column(Date, nullable=False)
    warning_3_on: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[DeadlineState] = mapped_column(String(16), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "iep_record_version_id",
            "rule_id",
            "source_kind",
            "source_ref",
            name="uq_compliance_deadline_derivation",
        ),
        CheckConstraint(
            "status IN ('upcoming', 'due', 'overdue')", name="ck_compliance_deadlines_status"
        ),
        Index("ix_compliance_deadlines_status_due", "status", "legal_due_on"),
        Index("ix_compliance_deadlines_student_ref", "student_ref"),
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
            "actor_role IN ('case_manager', 'compliance_admin', 'teacher', 'provider', 'system')",
            name="ck_audit_events_actor_role",
        ),
        Index("ix_audit_events_occurred_at", "occurred_at"),
        Index("ix_audit_events_event_type", "event_type"),
        Index("ix_audit_events_subject", "subject_type", "subject_ref"),
        Index("ix_audit_events_pipeline_run_id", "pipeline_run_id"),
    )
