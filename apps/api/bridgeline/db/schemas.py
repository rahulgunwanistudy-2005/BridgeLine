"""Pydantic models generated from the six canonical JSON Schema contracts.

The JSON files in ``packages/schemas`` are the source of truth. Cross-field rules
that JSON Schema cannot expose as ergonomic Python errors are repeated here as
model validators.
"""

import re
import unicodedata
from datetime import date, datetime, timedelta
from enum import StrEnum
from typing import Annotated, Self
from uuid import UUID

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    field_validator,
    model_validator,
)


def _require_utc(value: datetime) -> datetime:
    """Reject naive or non-UTC timestamps at the typed boundary."""

    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError("timestamp must be UTC RFC 3339")
    return value


UTCDateTime = Annotated[datetime, AfterValidator(_require_utc)]
NonEmptyString = Annotated[str, Field(min_length=1)]
PositiveInteger = Annotated[int, Field(ge=1)]
UnitInterval = Annotated[float, Field(ge=0.0, le=1.0)]


class ContractModel(BaseModel):
    """Base configuration shared by generated contract models."""

    model_config = ConfigDict(extra="forbid", strict=True)


class AccommodationScope(StrEnum):
    """Source-grounded applicability dimension for an accommodation."""

    SUBJECT = "subject"
    CONTEXT = "context"
    ALL = "all"


def _scope_match_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    return re.sub(r"\s+", " ", normalized).strip().casefold()


class ReconciliationStatus(StrEnum):
    """Identity result when an extracted item is compared with the prior IEP version."""

    MATCHED = "matched"
    NEW = "new"
    AMBIGUOUS = "ambiguous"


class AccommodationScopeReference(ContractModel):
    """One verbatim, independently grounded applicability reference."""

    scope: AccommodationScope = Field(description="Applicability dimension stated in the IEP.")
    ref: NonEmptyString = Field(description="Scope name or phrase stated in the document.")
    source_page: PositiveInteger = Field(description="One-based page containing scope evidence.")
    source_quote: NonEmptyString = Field(
        description="Verbatim source excerpt supporting the scope reference."
    )
    confidence: UnitInterval = Field(
        description="Extraction confidence from 0.0 to 1.0 for this scope reference."
    )


class Accommodation(ContractModel):
    """Approved accommodation with stable identity and source evidence."""

    id: UUID = Field(
        description=(
            "Stable UUID carried forward when this accommodation is reconciled across extractions."
        )
    )
    text: NonEmptyString = Field(description="Exact approved accommodation language.")
    applies_to_refs: Annotated[list[AccommodationScopeReference], Field(min_length=1)] = Field(
        description="Source-grounded applicability references used for deterministic fan-out."
    )
    source_page: PositiveInteger = Field(
        description="One-based page containing the accommodation evidence."
    )
    source_quote: NonEmptyString = Field(
        description="Verbatim source excerpt supporting the accommodation."
    )
    confidence: UnitInterval = Field(
        description="Extraction confidence from 0.0 to 1.0 for this accommodation."
    )
    reconciliation_status: ReconciliationStatus | None = Field(
        description=(
            "Identity result against the prior approved extraction, or null on the first "
            "extraction in the IEP lineage."
        )
    )

    @model_validator(mode="after")
    def validate_scope_references(self) -> Self:
        """Make unconstrained scope exclusive and reject semantic duplicate references."""

        all_references = [
            reference
            for reference in self.applies_to_refs
            if reference.scope is AccommodationScope.ALL
        ]
        if all_references and len(self.applies_to_refs) != 1:
            raise ValueError("all scope must be the only scope reference")
        normalized_keys = {
            (reference.scope, _scope_match_key(reference.ref)) for reference in self.applies_to_refs
        }
        if len(normalized_keys) != len(self.applies_to_refs):
            raise ValueError("scope references must be semantically unique")
        return self


class Service(ContractModel):
    """Mandated service schedule with stable identity and source evidence."""

    id: UUID = Field(
        description=(
            "Stable UUID carried forward when this service is reconciled across extractions."
        )
    )
    type: NonEmptyString = Field(description="Type of mandated special-education service.")
    minutes_per_week: PositiveInteger = Field(
        description="Normalized number of service minutes mandated each week."
    )
    frequency: NonEmptyString = Field(description="Service schedule language from the IEP.")
    provider_role: NonEmptyString = Field(
        description="Role responsible for delivering the service."
    )
    start: date | None = Field(
        description="School-local service start date, or null when unavailable."
    )
    end: date | None = Field(description="School-local service end date, or null when unavailable.")
    source_page: PositiveInteger = Field(
        description="One-based page containing the service evidence."
    )
    source_quote: NonEmptyString = Field(
        description="Verbatim source excerpt supporting the service."
    )
    confidence: UnitInterval = Field(
        description="Extraction confidence from 0.0 to 1.0 for this service."
    )
    reconciliation_status: ReconciliationStatus | None = Field(
        description=(
            "Identity result against the prior approved extraction, or null on the first "
            "extraction in the IEP lineage."
        )
    )

    @model_validator(mode="after")
    def validate_date_order(self) -> Self:
        """Ensure a known service end date does not precede its start date."""

        if self.start is not None and self.end is not None and self.end < self.start:
            raise ValueError("service end must be on or after service start")
        return self


class Goal(ContractModel):
    """Measurable annual goal with stable identity and source evidence."""

    id: UUID = Field(
        description="Stable UUID carried forward when this goal is reconciled across extractions."
    )
    text: NonEmptyString = Field(description="Complete approved annual goal language.")
    baseline: NonEmptyString = Field(description="Starting performance for goal measurement.")
    target: NonEmptyString = Field(description="Expected performance defining goal attainment.")
    measure: NonEmptyString = Field(description="Method used to measure progress toward the goal.")
    progress_cadence: NonEmptyString = Field(
        description="Required frequency for collecting or reporting progress."
    )
    source_page: PositiveInteger = Field(description="One-based page containing the goal evidence.")
    source_quote: NonEmptyString = Field(description="Verbatim source excerpt supporting the goal.")
    confidence: UnitInterval = Field(
        description="Extraction confidence from 0.0 to 1.0 for this goal."
    )
    reconciliation_status: ReconciliationStatus | None = Field(
        description=(
            "Identity result against the prior approved extraction, or null on the first "
            "extraction in the IEP lineage."
        )
    )


class IEPDates(ContractModel):
    """School-local compliance dates that must never undergo timezone conversion."""

    annual_review: date | None = Field(
        description="School-local annual-review deadline, or null when unavailable."
    )
    triennial_reeval: date | None = Field(
        description="School-local triennial-reevaluation deadline, or null when unavailable."
    )
    last_progress_report: date | None = Field(
        description="School-local date of the latest progress report, or null when unavailable."
    )


class FieldConfidences(ContractModel):
    """Extraction confidence for canonical scalar and date fields."""

    student_ref: UnitInterval = Field(
        description=(
            "Extraction confidence for student_ref; 0.0 required when the value is absent "
            "or unreliable."
        )
    )
    disability_category: UnitInterval = Field(
        description=(
            "Extraction confidence for disability_category; 0.0 required when the value is "
            "absent or unreliable."
        )
    )
    school_year: UnitInterval = Field(
        description=(
            "Extraction confidence for school_year; 0.0 required when the value is absent "
            "or unreliable."
        )
    )
    annual_review: UnitInterval = Field(
        description=(
            "Extraction confidence for annual_review; 0.0 required when the value is absent "
            "or unreliable."
        )
    )
    triennial_reeval: UnitInterval = Field(
        description=(
            "Extraction confidence for triennial_reeval; 0.0 required when the value is absent "
            "or unreliable."
        )
    )
    last_progress_report: UnitInterval = Field(
        description=(
            "Extraction confidence for last_progress_report; 0.0 required when the value is "
            "absent or unreliable."
        )
    )


class ExtractionMeta(ContractModel):
    """Provenance for one extraction attempt."""

    model: NonEmptyString = Field(description="Pinned model identifier used for extraction.")
    run_id: UUID = Field(description="UUID unique to this extraction attempt.")
    page_count: PositiveInteger = Field(description="Number of source pages processed.")
    legibility_scores: Annotated[list[UnitInterval], Field(min_length=1)] = Field(
        description="Per-page legibility scores from 0.0 to 1.0 in page order."
    )
    extracted_at: UTCDateTime = Field(description="UTC timestamp when the extraction completed.")


class IEPRecord(ContractModel):
    """Canonical source-grounded extraction of one physical IEP lineage."""

    iep_record_id: UUID = Field(
        description="Stable UUID preserved across extractions of the same physical IEP."
    )
    student_ref: NonEmptyString = Field(description="District identifier for the student.")
    disability_category: NonEmptyString = Field(
        description="Eligibility category stated in the approved IEP."
    )
    school_year: str = Field(
        pattern=r"^[0-9]{4}-[0-9]{4}$",
        description="Consecutive school years in YYYY-YYYY form.",
    )
    accommodations: list[Accommodation] = Field(
        description="Approved accommodations with stable identities and source evidence."
    )
    services: list[Service] = Field(
        description="Mandated services with stable identities and source evidence."
    )
    goals: list[Goal] = Field(
        description="Annual goals with stable identities and source evidence."
    )
    dates: IEPDates = Field(description="School-local compliance dates.")
    field_confidences: FieldConfidences = Field(
        description="Extraction confidence for canonical scalar and date fields."
    )
    extraction_meta: ExtractionMeta = Field(description="Provenance for this extraction run.")

    @field_validator("school_year")
    @classmethod
    def validate_consecutive_school_year(cls, value: str) -> str:
        """Require the second school-year component to immediately follow the first."""

        first_year, second_year = (int(part) for part in value.split("-"))
        if second_year != first_year + 1:
            raise ValueError("school_year must contain consecutive years")
        return value

    @model_validator(mode="after")
    def validate_legibility_score_count(self) -> Self:
        """Require one legibility score for every source page."""

        if len(self.extraction_meta.legibility_scores) != self.extraction_meta.page_count:
            raise ValueError("legibility_scores must contain exactly one score per page")
        return self


class ObligationStatus(StrEnum):
    """Teacher workflow state for an obligation."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    FLAGGED = "flagged"


class AssigneeKind(StrEnum):
    """Kinds of people who can receive implementation obligations."""

    TEACHER = "teacher"
    PROVIDER = "provider"


class ObligationContextKind(StrEnum):
    """Contexts in which an assignee implements an obligation."""

    STUDENT = "student"
    CLASS = "class"
    SERVICE = "service"


class ObligationSourceKind(StrEnum):
    """Approved IEP source objects supporting an obligation."""

    IEP_RECORD = "iep_record"
    ACCOMMODATION = "accommodation"
    SERVICE = "service"


class ObligationScopeProvenance(ContractModel):
    """Approved scope evidence that caused one accommodation obligation."""

    scope: AccommodationScope = Field(description="Contributing applicability dimension.")
    ref: NonEmptyString = Field(description="Scope phrase copied from the approved IEPRecord.")
    source_page: PositiveInteger = Field(description="One-based source page for the scope.")
    source_quote: NonEmptyString = Field(
        description="Verbatim source excerpt supporting the scope."
    )
    confidence: UnitInterval = Field(description="Approved extraction confidence for the scope.")


class Obligation(ContractModel):
    """Deterministically derived implementation requirement."""

    id: UUID = Field(description="Stable UUID identifying this teacher obligation.")
    student_ref: NonEmptyString = Field(description="District identifier for the student.")
    source_kind: ObligationSourceKind = Field(description="Kind of approved IEP source object.")
    source_ref: UUID = Field(description="Stable UUID of the approved source object.")
    scope_provenance: list[ObligationScopeProvenance] = Field(
        description="Approved scope references that caused this obligation."
    )
    rule_id: NonEmptyString = Field(description="Identifier of the deterministic rule used.")
    citation: NonEmptyString = Field(description="Legal or policy citation for the rule.")
    action_text: NonEmptyString = Field(
        description="Mandatory action produced only by the deterministic rules engine."
    )
    practice_text: str | None = Field(
        description="LLM-authored subject guidance, or null before brief generation."
    )
    status: ObligationStatus = Field(description="Current teacher workflow state.")
    confirmed_at: UTCDateTime | None = Field(
        description="UTC confirmation timestamp when confirmed, otherwise null."
    )
    flag_reason: str | None = Field(description="Teacher explanation when flagged, otherwise null.")

    @model_validator(mode="after")
    def validate_status_details(self) -> Self:
        """Keep confirmation and flag details consistent with the obligation state."""

        if self.source_kind is ObligationSourceKind.ACCOMMODATION:
            if not self.scope_provenance:
                raise ValueError("accommodation obligations require scope_provenance")
        elif self.scope_provenance:
            raise ValueError("scope_provenance is valid only for accommodation obligations")
        if self.status is ObligationStatus.CONFIRMED:
            if self.confirmed_at is None:
                raise ValueError("confirmed obligations require confirmed_at")
        elif self.confirmed_at is not None:
            raise ValueError("confirmed_at must be null unless status is confirmed")
        if self.status is ObligationStatus.FLAGGED:
            if self.flag_reason is None or not self.flag_reason.strip():
                raise ValueError("flagged obligations require flag_reason")
        elif self.flag_reason is not None:
            raise ValueError("flag_reason must be null unless status is flagged")
        return self


class ObligationSet(ContractModel):
    """Legal implementation obligations grouped by assignee and context."""

    assignee_kind: AssigneeKind = Field(description="Kind of responsible assignee.")
    assignee_ref: NonEmptyString = Field(description="District identifier for the assignee.")
    assignee_role: NonEmptyString = Field(description="Implementation role of the assignee.")
    context_kind: ObligationContextKind = Field(description="Kind of implementation context.")
    context_ref: NonEmptyString = Field(description="Stable identifier for the context.")
    subject: str | None = Field(description="Class subject, or null outside a class context.")
    generated_at: UTCDateTime = Field(description="UTC timestamp of deterministic generation.")
    rules_version: NonEmptyString = Field(description="Rule-registry version used.")
    obligations: list[Obligation] = Field(description="Derived teacher obligations.")


class BriefStatus(StrEnum):
    """Delivery lifecycle state for a teacher brief."""

    DRAFT = "draft"
    RELEASED = "released"
    CONFIRMED = "confirmed"
    FLAGGED = "flagged"


class Responsibility(ContractModel):
    """Teacher responsibility statement and legal authority."""

    text: NonEmptyString = Field(description="Actionable teacher responsibility statement.")
    citation: NonEmptyString = Field(description="Legal citation supporting the statement.")


class BriefObligation(ContractModel):
    """One source-grounded obligation rendered in a teacher brief."""

    obligation_id: UUID = Field(description="UUID of the deterministic obligation.")
    accommodation_id: UUID = Field(description="Stable UUID of the source accommodation.")
    accommodation_text: NonEmptyString = Field(description="Exact approved accommodation language.")
    action_text: NonEmptyString = Field(
        description="Mandatory deterministic action copied without modification."
    )
    practice_text: NonEmptyString = Field(
        description="LLM-authored subject-specific implementation guidance."
    )
    source_page: PositiveInteger = Field(description="One-based source IEP page.")
    source_quote: NonEmptyString = Field(description="Verbatim supporting IEP excerpt.")
    source_confidence: UnitInterval = Field(
        description="Approved confidence inherited from the source accommodation."
    )
    rule_id: NonEmptyString = Field(description="Identifier of the deterministic rule.")
    citation: NonEmptyString = Field(description="Legal or policy citation for the rule.")


class StudentBrief(ContractModel):
    """Authorized class-specific implementation information for one student."""

    student_ref: NonEmptyString = Field(description="District identifier for the student.")
    student_name: NonEmptyString = Field(description="Authorized student display name.")
    obligations: list[BriefObligation] = Field(description="Student obligations for the class.")


class TeacherBrief(ContractModel):
    """One-class teacher brief preserving deterministic obligations."""

    brief_id: UUID = Field(description="UUID identifying this brief.")
    teacher_ref: NonEmptyString = Field(description="District identifier for the teacher.")
    class_ref: NonEmptyString = Field(description="District identifier for the class.")
    subject: NonEmptyString = Field(description="Instructional subject for the brief.")
    school_year: str = Field(
        pattern=r"^[0-9]{4}-[0-9]{4}$",
        description="Consecutive school years in YYYY-YYYY form.",
    )
    generated_at: UTCDateTime = Field(description="UTC timestamp when the brief was generated.")
    rules_version: NonEmptyString = Field(description="Rule-registry version used.")
    status: BriefStatus = Field(description="Current brief delivery state.")
    released_at: UTCDateTime | None = Field(
        description="UTC release timestamp after case-manager release, otherwise null."
    )
    confirmed_at: UTCDateTime | None = Field(
        description="UTC teacher-confirmation timestamp, otherwise null."
    )
    flag_reason: str | None = Field(
        description="Teacher explanation when the brief is flagged, otherwise null."
    )
    responsibility: Responsibility = Field(
        description="Teacher responsibility statement and citation."
    )
    students: list[StudentBrief] = Field(description="Authorized student sections.")

    @field_validator("school_year")
    @classmethod
    def validate_consecutive_school_year(cls, value: str) -> str:
        """Require the second school-year component to immediately follow the first."""

        first_year, second_year = (int(part) for part in value.split("-"))
        if second_year != first_year + 1:
            raise ValueError("school_year must contain consecutive years")
        return value

    @model_validator(mode="after")
    def validate_status_details(self) -> Self:
        """Keep release, confirmation, and flag details consistent with brief state."""

        if self.status is BriefStatus.DRAFT:
            if self.released_at is not None:
                raise ValueError("draft briefs must not have released_at")
        elif self.released_at is None:
            raise ValueError("non-draft briefs require released_at")
        if self.status is BriefStatus.CONFIRMED:
            if self.confirmed_at is None:
                raise ValueError("confirmed briefs require confirmed_at")
        elif self.confirmed_at is not None:
            raise ValueError("confirmed_at must be null unless status is confirmed")
        if self.status is BriefStatus.FLAGGED:
            if self.flag_reason is None or not self.flag_reason.strip():
                raise ValueError("flagged briefs require flag_reason")
        elif self.flag_reason is not None:
            raise ValueError("flag_reason must be null unless status is flagged")
        return self


class SignalType(StrEnum):
    """Origin category for a normalized progress signal."""

    GRADE = "grade"
    SERVICE_MINUTES = "service_minutes"
    TEACHER_CHECK_IN = "teacher_check_in"


class ActorRole(StrEnum):
    """Human or system roles that may record progress evidence."""

    TEACHER = "teacher"
    PROVIDER = "provider"
    CASE_MANAGER = "case_manager"
    SYSTEM = "system"


class SignalActor(ContractModel):
    """Actor responsible for a progress observation."""

    actor_ref: NonEmptyString = Field(description="District or system actor identifier.")
    actor_role: ActorRole = Field(description="Role under which the signal was recorded.")


class Measurement(ContractModel):
    """Exactly one numeric or textual normalized observation."""

    metric: NonEmptyString = Field(description="Stable label for the measured quantity.")
    numeric_value: float | None = Field(
        description="Quantitative value, or null for a textual observation."
    )
    text_value: str | None = Field(
        description="Narrative value, or null for a quantitative observation."
    )
    unit: str | None = Field(description="Numeric unit, or null when not applicable.")

    @model_validator(mode="after")
    def require_exactly_one_value(self) -> Self:
        """Reject missing and ambiguous measurements from deterministic imports."""

        populated = (self.numeric_value is not None) + (self.text_value is not None)
        if populated != 1:
            raise ValueError("exactly one of numeric_value or text_value must be populated")
        if self.text_value is not None and not self.text_value.strip():
            raise ValueError("text_value must be non-empty when populated")
        return self


class SignalSource(ContractModel):
    """Retrievable source evidence for a normalized signal."""

    source_name: NonEmptyString = Field(description="File, form, or source-system name.")
    source_record_ref: NonEmptyString = Field(description="Stable source row identifier.")
    source_excerpt: NonEmptyString = Field(description="Raw excerpt supporting the signal.")


class GoalMappingStatus(StrEnum):
    """Review state for mapping a signal to an IEP goal."""

    UNMAPPED = "unmapped"
    AUTO_MAPPED = "auto_mapped"
    CONFIRMED = "confirmed"
    NEEDS_REVIEW = "needs_review"


class GoalMapping(ContractModel):
    """Reviewable connection between a signal and an IEP goal."""

    goal_id: UUID | None = Field(description="Stable goal UUID, or null when unmapped.")
    status: GoalMappingStatus = Field(description="Current goal-mapping workflow state.")
    confidence: UnitInterval | None = Field(
        description="Mapping confidence from 0.0 to 1.0, or null when unmapped."
    )
    rationale: str | None = Field(
        description="Evidence-based mapping explanation, or null when unmapped."
    )

    @model_validator(mode="after")
    def validate_mapping_details(self) -> Self:
        """Require complete details for mapped states and none for unmapped state."""

        details = (self.goal_id, self.confidence, self.rationale)
        if self.status is GoalMappingStatus.UNMAPPED:
            if any(value is not None for value in details):
                raise ValueError("unmapped signals must not contain mapping details")
        elif any(value is None for value in details):
            raise ValueError("mapped signals require goal_id, confidence, and rationale")
        elif self.rationale is not None and not self.rationale.strip():
            raise ValueError("mapping rationale must be non-empty")
        return self


class ProgressSignal(ContractModel):
    """Normalized source-linked observation used for goal reconciliation."""

    signal_id: UUID = Field(description="UUID identifying this normalized signal.")
    student_ref: NonEmptyString = Field(description="District identifier for the student.")
    signal_type: SignalType = Field(description="Category of source observation.")
    observed_at: UTCDateTime = Field(description="UTC timestamp of the observation.")
    ingested_at: UTCDateTime = Field(description="UTC timestamp of normalization.")
    recorded_by: SignalActor = Field(description="Actor responsible for the observation.")
    measurement: Measurement = Field(description="Exactly one normalized measurement value.")
    source: SignalSource = Field(description="Retrievable source evidence.")
    goal_mapping: GoalMapping = Field(description="Reviewable mapping to an IEP goal.")


class AuditActorRole(StrEnum):
    """Roles that may perform consequential audited actions."""

    CASE_MANAGER = "case_manager"
    COMPLIANCE_ADMIN = "compliance_admin"
    TEACHER = "teacher"
    PROVIDER = "provider"
    SYSTEM = "system"


class AuditActor(ContractModel):
    """Actor responsible for an audited action."""

    actor_ref: NonEmptyString = Field(description="District or system actor identifier.")
    actor_role: AuditActorRole = Field(description="Authorized role used for the action.")


class AuditSubject(ContractModel):
    """Primary domain record affected by an audited action."""

    subject_type: NonEmptyString = Field(description="Domain type of the affected record.")
    subject_ref: NonEmptyString = Field(description="Stable identifier of the affected record.")


class AuditChange(ContractModel):
    """Field-level before-and-after values for an audited action."""

    field_path: NonEmptyString = Field(description="JSON-path-like location of the field.")
    previous_value: JsonValue = Field(description="JSON value before the action, or null.")
    new_value: JsonValue = Field(description="JSON value after the action, or null.")


class EvidenceType(StrEnum):
    """Kinds of evidence that may support an audited action."""

    IEP_SOURCE = "iep_source"
    RULE_CITATION = "rule_citation"
    PROGRESS_SIGNAL = "progress_signal"
    DOCUMENT = "document"
    AUDIT_EVENT = "audit_event"


class EvidenceReference(ContractModel):
    """Retrievable evidence supporting an audited action."""

    evidence_type: EvidenceType = Field(description="Controlled evidence category.")
    evidence_ref: NonEmptyString = Field(description="Stable evidence identifier.")
    locator: str | None = Field(description="Precise location within the evidence, or null.")


class AuditEvent(ContractModel):
    """Immutable actor-attributed record of a consequential action."""

    event_id: UUID = Field(description="UUID identifying this append-only event.")
    event_type: str = Field(
        pattern=r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$",
        description="Lowercase dotted action name used for event routing.",
    )
    occurred_at: UTCDateTime = Field(description="UTC timestamp when the action occurred.")
    summary: NonEmptyString = Field(description="Human-readable factual action summary.")
    actor: AuditActor = Field(description="Actor responsible for the action.")
    subject: AuditSubject = Field(description="Primary affected domain record.")
    changes: list[AuditChange] = Field(description="Field-level before-and-after values.")
    evidence: list[EvidenceReference] = Field(description="Evidence supporting the action.")
    correlation_id: UUID | None = Field(description="Related-operation UUID, or null.")
    run_id: UUID | None = Field(description="Originating pipeline-run UUID, or null.")


class PipelineState(StrEnum):
    """Controlled lifecycle states for pipeline stages."""

    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    NEEDS_REVIEW = "needs_review"
    ERROR = "error"


class PipelineStatusEvent(ContractModel):
    """Persisted event driving the resumable pipeline visualization."""

    run_id: UUID = Field(description="UUID of the pipeline run.")
    seq: PositiveInteger = Field(description="Monotonic run-local SSE resume cursor.")
    stage: NonEmptyString = Field(description="Stable machine-readable stage slug.")
    agent_label: NonEmptyString = Field(description="Human-facing agent or component name.")
    state: PipelineState = Field(description="Controlled stage lifecycle state.")
    detail: NonEmptyString = Field(description="User-facing explanation of current work.")
    progress: UnitInterval | None = Field(
        description="Fractional completion from 0.0 to 1.0, or null."
    )
    parent_stage: str | None = Field(
        description="Fan-out parent stage slug, or null for a top-level stage."
    )
    ts: UTCDateTime = Field(description="UTC timestamp when the event was persisted.")
