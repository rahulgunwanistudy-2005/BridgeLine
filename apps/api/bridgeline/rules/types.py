"""Frozen domain inputs and outputs for deterministic compliance rules."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Annotated
from uuid import UUID, uuid5

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from bridgeline.db.schemas import AccommodationScope, IEPRecord, UTCDateTime

RULES_NAMESPACE = UUID("16704037-bc24-4fcc-9f00-d5728cc25138")
NonEmpty = Annotated[str, Field(min_length=1)]


class RulesModel(BaseModel):
    """Strict immutable base for rule-boundary values."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class AssigneeKind(StrEnum):
    """Kinds of people receiving obligations."""

    TEACHER = "teacher"
    PROVIDER = "provider"


class ContextKind(StrEnum):
    """Implementation contexts for obligations."""

    STUDENT = "student"
    CLASS = "class"
    SERVICE = "service"


class SourceKind(StrEnum):
    """Approved IEP source objects supporting obligations."""

    IEP_RECORD = "iep_record"
    ACCOMMODATION = "accommodation"
    SERVICE = "service"
    GOAL = "goal"


class ScopeMappingKind(StrEnum):
    """Authorized deterministic sources for a roster scope mapping."""

    HUMAN_RESOLUTION = "human_resolution"
    DISTRICT_ALIAS = "district_alias"


class FindingSeverity(StrEnum):
    """Review priority for deterministic findings."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class FindingStatus(StrEnum):
    """Lifecycle state of a finding."""

    OPEN = "open"
    RESOLVED = "resolved"


class DeadlineStatus(StrEnum):
    """State of a legal deadline relative to the school-local as-of date."""

    UPCOMING = "upcoming"
    DUE = "due"
    OVERDUE = "overdue"


class TermKind(StrEnum):
    """School-calendar term categories used by deterministic cadence rules."""

    SEMESTER = "semester"
    GRADING_PERIOD = "grading_period"


class TeacherAssignment(RulesModel):
    """Teacher-of-record assignment for one class."""

    teacher_ref: NonEmpty
    role: NonEmpty = "teacher-of-record"


class RosterClass(RulesModel):
    """Active class context and all teachers-of-record."""

    class_ref: NonEmpty
    subject: NonEmpty
    teachers: tuple[TeacherAssignment, ...]


class ScopeReferenceMapping(RulesModel):
    """Approved mapping from document language to one roster vocabulary value."""

    scope: AccommodationScope
    document_ref: NonEmpty
    target_ref: NonEmpty
    kind: ScopeMappingKind
    accommodation_id: UUID | None = None


class ProviderAssignment(RulesModel):
    """Provider-of-record assignment for one approved service."""

    service_id: UUID
    provider_ref: NonEmpty
    provider_role: NonEmpty


class BriefSnapshot(RulesModel):
    """School-local delivery and confirmation state for one teacher brief."""

    brief_id: UUID
    class_ref: NonEmpty
    teacher_ref: NonEmpty
    status: NonEmpty
    released_on: date | None = None


class AccommodationClassState(RulesModel):
    """Aggregated teacher confirmation state for one accommodation in one class."""

    accommodation_id: UUID
    class_ref: NonEmpty
    obligation_refs: tuple[UUID, ...]
    confirmed: bool


class ServiceDelayReason(RulesModel):
    """Documented operational reason for a delayed service start."""

    service_id: UUID
    reason: NonEmpty


class ServiceDeliveryLog(RulesModel):
    """One source service-delivery event used in weekly accounting."""

    log_id: UUID
    service_id: UUID
    delivered_on: date
    minutes: Annotated[int, Field(gt=0)]
    provider_ref: NonEmpty
    substitute_for_ref: str | None = None
    makeup_for_week_start: date | None = None


class CalendarDay(RulesModel):
    """One school-local date and whether instruction occurs."""

    day: date
    instructional: bool


class SchoolTerm(RulesModel):
    """Named semester or grading period on the district calendar."""

    term_ref: NonEmpty
    kind: TermKind
    start_on: date
    end_on: date


class ComplianceProfile(RulesModel):
    """Student facts not represented inside an approved existing-IEP document."""

    initial_eligibility: bool = False
    eligibility_determined_on: date | None = None


class ApprovedRecord(RulesModel):
    """Canonical record paired with its approved immutable database row."""

    row_id: UUID
    student_id: UUID
    record: IEPRecord
    approved_on: date | None = None


class RosterSnapshot(RulesModel):
    """All deterministic assignment facts used for one derivation."""

    classes: tuple[RosterClass, ...]
    providers: tuple[ProviderAssignment, ...]
    scope_mappings: tuple[ScopeReferenceMapping, ...] = ()
    briefs: tuple[BriefSnapshot, ...] = ()
    accommodation_classes: tuple[AccommodationClassState, ...] = ()
    service_delay_reasons: tuple[ServiceDelayReason, ...] = ()
    service_start_delay_school_days: Annotated[int, Field(ge=0)] = 5
    service_logs: tuple[ServiceDeliveryLog, ...] = ()
    calendar_days: tuple[CalendarDay, ...] = ()
    terms: tuple[SchoolTerm, ...] = ()
    compliance_profile: ComplianceProfile = ComplianceProfile()
    generated_at: UTCDateTime
    as_of: date


class ScopeProvenance(RulesModel):
    """Approved document scope that contributed to an obligation."""

    scope: AccommodationScope
    ref: NonEmpty
    source_page: Annotated[int, Field(ge=1)]
    source_quote: NonEmpty
    confidence: Annotated[float, Field(ge=0.0, le=1.0)]


class DerivedObligation(RulesModel):
    """One deterministic implementation requirement."""

    id: UUID
    student_ref: NonEmpty
    assignee_kind: AssigneeKind
    assignee_ref: NonEmpty
    assignee_role: NonEmpty
    context_kind: ContextKind
    context_ref: NonEmpty
    subject: str | None
    source_kind: SourceKind
    source_ref: UUID
    scope_provenance: tuple[ScopeProvenance, ...] = ()
    rule_id: NonEmpty
    citation: NonEmpty
    action_text: NonEmpty
    practice_text: str | None = None
    status: str = "pending"
    confirmed_at: datetime | None = None
    flag_reason: str | None = None


class Finding(RulesModel):
    """Source-linked deterministic compliance finding."""

    id: UUID
    rule_id: NonEmpty
    citation: NonEmpty
    finding_type: NonEmpty
    severity: FindingSeverity
    student_ref: NonEmpty
    iep_record_version_id: UUID | None
    detected_on: date
    title: NonEmpty
    detail: NonEmpty
    related_refs: dict[str, JsonValue]
    measurements: dict[str, JsonValue]
    status: FindingStatus = FindingStatus.OPEN


class Deadline(RulesModel):
    """One cited calendar obligation with adjusted school action dates."""

    id: UUID
    rule_id: NonEmpty
    citation: NonEmpty
    student_ref: NonEmpty
    iep_record_version_id: UUID
    source_kind: SourceKind
    source_ref: UUID
    legal_due_on: date
    action_due_on: date
    warning_30_on: date
    warning_14_on: date
    warning_3_on: date
    status: DeadlineStatus
    description: NonEmpty


class RuleState(RulesModel):
    """State inspected by a rule's deterministic checks."""

    approved: ApprovedRecord
    roster: RosterSnapshot


class RosterStudent(RulesModel):
    """One active district roster student and current approved-version state."""

    student_ref: NonEmpty
    school_year: NonEmpty
    current_approved_iep_version_id: UUID | None = None


class DistrictRuleState(RulesModel):
    """District-wide roster state used by baseline compliance checks."""

    students: tuple[RosterStudent, ...]
    as_of: date


class DerivationResult(RulesModel):
    """Canonical output of running the registry once."""

    generated_at: UTCDateTime
    rules_version: NonEmpty
    obligations: tuple[DerivedObligation, ...]
    deadlines: tuple[Deadline, ...]
    findings: tuple[Finding, ...]


def obligation_id(
    approved: ApprovedRecord,
    *,
    rule_id: str,
    source_kind: SourceKind,
    source_ref: UUID,
    assignee_kind: AssigneeKind,
    assignee_ref: str,
    context_kind: ContextKind,
    context_ref: str,
) -> UUID:
    """Derive the stable identity of an obligation from its complete natural key."""

    key = "|".join(
        (
            str(approved.row_id),
            rule_id,
            source_kind.value,
            str(source_ref),
            assignee_kind.value,
            assignee_ref,
            context_kind.value,
            context_ref,
        )
    )
    return uuid5(RULES_NAMESPACE, key)


def finding_id(approved: ApprovedRecord, *, rule_id: str, finding_type: str, ref: str) -> UUID:
    """Derive a stable finding identity from its cited rule and subject."""

    return uuid5(RULES_NAMESPACE, f"{approved.row_id}|{rule_id}|{finding_type}|{ref}")


def district_finding_id(*, rule_id: str, finding_type: str, ref: str) -> UUID:
    """Derive a stable identity for a district-level finding without an IEP version."""

    return uuid5(RULES_NAMESPACE, f"district|{rule_id}|{finding_type}|{ref}")


def deadline_id(approved: ApprovedRecord, *, rule_id: str, source_ref: UUID) -> UUID:
    """Derive stable identity for one rule/source deadline."""

    return uuid5(RULES_NAMESPACE, f"{approved.row_id}|{rule_id}|deadline|{source_ref}")
