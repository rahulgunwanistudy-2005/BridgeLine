"""Persistence boundary for approved-version rule derivation."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, datetime
from typing import Literal, cast
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from pydantic import JsonValue
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bridgeline.config import get_settings
from bridgeline.db.iep_records import get_current_approved_record
from bridgeline.db.models import (
    AuditActorRole,
    AuditEvent,
    Brief,
    Class,
    ClassStaff,
    ComplianceDeadline,
    Enrollment,
    Provider,
    SchoolCalendarDay,
    SchoolTerm,
    ScopeReferenceAlias,
    ScopeReferenceResolution,
    ServiceAssignment,
    Student,
    StudentComplianceProfile,
    Teacher,
)
from bridgeline.db.models import (
    Finding as FindingRow,
)
from bridgeline.db.models import IEPRecord as IEPRecordRow
from bridgeline.db.models import (
    Obligation as ObligationRow,
)
from bridgeline.db.models import (
    ServiceDelayReason as ServiceDelayReasonRow,
)
from bridgeline.db.models import (
    ServiceDeliveryLog as ServiceDeliveryLogRow,
)
from bridgeline.db.schemas import (
    AccommodationScope,
    IEPRecord,
    ObligationContextKind,
    ObligationScopeProvenance,
    ObligationSet,
    ObligationSourceKind,
    ObligationStatus,
)
from bridgeline.db.schemas import (
    AssigneeKind as ContractAssigneeKind,
)
from bridgeline.db.schemas import (
    Obligation as ContractObligation,
)
from bridgeline.rules.engine import derive_district_findings, derive_obligations
from bridgeline.rules.registry import RULES_VERSION
from bridgeline.rules.scope_resolution import normalize_scope_text
from bridgeline.rules.types import (
    AccommodationClassState,
    ApprovedRecord,
    BriefSnapshot,
    CalendarDay,
    ComplianceProfile,
    Deadline,
    DeadlineStatus,
    DerivationResult,
    DerivedObligation,
    DistrictRuleState,
    Finding,
    FindingSeverity,
    FindingStatus,
    ProviderAssignment,
    RosterClass,
    RosterSnapshot,
    RosterStudent,
    ScopeMappingKind,
    ScopeReferenceMapping,
    ServiceDelayReason,
    ServiceDeliveryLog,
    SourceKind,
    TeacherAssignment,
    TermKind,
)
from bridgeline.rules.types import (
    SchoolTerm as RuleSchoolTerm,
)


class ApprovedRecordNotFoundError(LookupError):
    """No current approved version exists for the requested IEP lineage."""


class ObligationNotFoundError(LookupError):
    """The requested obligation does not exist."""


class InvalidObligationTransitionError(ValueError):
    """An obligation transition violates its workflow invariants."""


class FindingNotFoundError(LookupError):
    """The requested finding does not exist."""


class InvalidFindingTransitionError(ValueError):
    """A finding lifecycle transition is invalid."""


class InvalidServiceDelayReasonActorError(PermissionError):
    """Only a case manager may record or revoke a service-delay reason."""


class ServiceDelayReasonNotFoundError(LookupError):
    """The requested service-delay reason does not exist or is inactive."""


class InvalidScopeMappingActorError(PermissionError):
    """The actor role cannot perform the requested scope-mapping operation."""


class ScopeReferenceMappingNotFoundError(LookupError):
    """The requested alias, resolution, or source finding does not exist."""


class RulesRepository:
    """Load rule inputs and atomically persist new deterministic outputs."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def derive_and_persist(
        self,
        lineage_id: UUID,
        *,
        generated_at: datetime,
        as_of: date,
        derivation_run_id: UUID,
    ) -> DerivationResult:
        """Derive from the current approved row and insert only unseen identities."""

        approved = await self._load_approved(lineage_id)
        roster = await self._load_roster(approved, generated_at=generated_at, as_of=as_of)
        result = derive_obligations(approved, roster)
        obligation_ids = tuple(item.id for item in result.obligations)
        existing_obligations = (
            {}
            if not obligation_ids
            else {
                row.id: row
                for row in (
                    await self._session.scalars(
                        select(ObligationRow).where(ObligationRow.id.in_(obligation_ids))
                    )
                ).all()
            }
        )
        for obligation in result.obligations:
            existing_obligation = existing_obligations.get(obligation.id)
            if existing_obligation is None:
                self._session.add(_obligation_row(approved, obligation))
                self._session.add(_derived_event(approved, obligation, generated_at))
            else:
                scope_provenance = [
                    evidence.model_dump(mode="json") for evidence in obligation.scope_provenance
                ]
                if existing_obligation.scope_provenance != scope_provenance:
                    previous = existing_obligation.scope_provenance
                    existing_obligation.scope_provenance = scope_provenance
                    self._session.add(
                        _scope_provenance_event(
                            existing_obligation,
                            previous=previous,
                            occurred_at=generated_at,
                            derivation_run_id=derivation_run_id,
                        )
                    )
        for deadline in result.deadlines:
            existing_deadline = await self._session.get(ComplianceDeadline, deadline.id)
            if existing_deadline is None:
                self._session.add(_deadline_row(deadline))
                self._session.add(_deadline_event(approved, deadline, generated_at))
            else:
                event = _sync_deadline(existing_deadline, deadline, generated_at)
                if event is not None:
                    self._session.add(event)
        existing_findings = {
            row.id: row
            for row in (
                await self._session.scalars(
                    select(FindingRow).where(FindingRow.iep_record_version_id == approved.row_id)
                )
            ).all()
        }
        emitted_ids = {finding.id for finding in result.findings}
        for finding in result.findings:
            existing = existing_findings.get(finding.id)
            if existing is None:
                self._session.add(_finding_row(finding))
                self._session.add(_finding_opened_event(finding, generated_at, derivation_run_id))
            elif existing.status == "resolved":
                existing.status = "open"
                existing.resolved_at = None
                _update_finding(existing, finding)
                self._session.add(
                    _finding_transition_event(
                        existing,
                        previous="resolved",
                        actor_ref="rules-engine",
                        actor_role="system",
                        occurred_at=generated_at,
                        derivation_run_id=derivation_run_id,
                        reason=(
                            "The deterministic re-derivation emitted this finding again: "
                            f"{finding.detail}"
                        ),
                    )
                )
            else:
                _update_finding(existing, finding)
        for existing in existing_findings.values():
            if existing.status == "open" and existing.id not in emitted_ids:
                existing.status = "resolved"
                existing.resolved_at = generated_at
                self._session.add(
                    _finding_transition_event(
                        existing,
                        previous="open",
                        actor_ref="rules-engine",
                        actor_role="system",
                        occurred_at=generated_at,
                        derivation_run_id=derivation_run_id,
                        reason=("The deterministic re-derivation no longer emitted this finding."),
                    )
                )
        await self._session.commit()
        return result

    async def transition_obligation(
        self,
        obligation_id: UUID,
        *,
        status: Literal["confirmed", "flagged"],
        actor_ref: str,
        actor_role: AuditActorRole,
        occurred_at: datetime,
        flag_reason: str | None = None,
    ) -> None:
        """Change workflow state and append its audit event in one transaction."""

        row = await self._session.get(ObligationRow, obligation_id)
        if row is None:
            raise ObligationNotFoundError(f"obligation {obligation_id} does not exist")
        if row.status != "pending" or status not in {"confirmed", "flagged"}:
            raise InvalidObligationTransitionError(
                f"cannot transition obligation from {row.status} to {status}"
            )
        if status == "flagged" and (flag_reason is None or not flag_reason.strip()):
            raise InvalidObligationTransitionError("flagged obligations require a reason")
        if status == "confirmed" and flag_reason is not None:
            raise InvalidObligationTransitionError(
                "confirmed obligations cannot have a flag reason"
            )
        previous = row.status
        row.status = status
        row.confirmed_at = occurred_at if status == "confirmed" else None
        row.flag_reason = flag_reason if status == "flagged" else None
        self._session.add(
            _transition_event(
                row,
                previous=previous,
                actor_ref=actor_ref,
                actor_role=actor_role,
                occurred_at=occurred_at,
            )
        )
        await self._session.commit()

    async def obligation_sets(self, lineage_id: UUID) -> tuple[ObligationSet, ...]:
        """Return persisted obligations grouped in canonical assignee/context order."""

        approved = await self._load_approved(lineage_id)
        statement = (
            select(ObligationRow)
            .where(ObligationRow.iep_record_version_id == approved.row_id)
            .order_by(
                ObligationRow.assignee_kind,
                ObligationRow.assignee_ref,
                ObligationRow.context_kind,
                ObligationRow.context_ref,
                ObligationRow.rule_id,
                ObligationRow.source_ref,
            )
        )
        rows = tuple((await self._session.scalars(statement)).all())
        grouped: defaultdict[tuple[str, str, str, str, str, str | None], list[ObligationRow]] = (
            defaultdict(list)
        )
        for row in rows:
            grouped[
                (
                    row.assignee_kind,
                    row.assignee_ref,
                    row.assignee_role,
                    row.context_kind,
                    row.context_ref,
                    row.subject,
                )
            ].append(row)
        return tuple(_obligation_set(key, values, approved) for key, values in grouped.items())

    async def deadlines(
        self, *, student_ref: str | None = None, status: str | None = None
    ) -> tuple[Deadline, ...]:
        """Return persisted deadlines with stable ordering and optional filters."""

        statement = select(ComplianceDeadline)
        if student_ref is not None:
            statement = statement.where(ComplianceDeadline.student_ref == student_ref)
        if status is not None:
            statement = statement.where(ComplianceDeadline.status == status)
        statement = statement.order_by(
            ComplianceDeadline.legal_due_on,
            ComplianceDeadline.student_ref,
            ComplianceDeadline.rule_id,
            ComplianceDeadline.source_ref,
        )
        rows = tuple((await self._session.scalars(statement)).all())
        return tuple(
            Deadline(
                id=row.id,
                rule_id=row.rule_id,
                citation=row.citation,
                student_ref=row.student_ref,
                iep_record_version_id=row.iep_record_version_id,
                source_kind=SourceKind(row.source_kind),
                source_ref=row.source_ref,
                legal_due_on=row.legal_due_on,
                action_due_on=row.action_due_on,
                warning_30_on=row.warning_30_on,
                warning_14_on=row.warning_14_on,
                warning_3_on=row.warning_3_on,
                status=DeadlineStatus(row.status),
                description=row.description,
            )
            for row in rows
        )

    async def findings(
        self,
        *,
        student_ref: str | None = None,
        status: str | None = None,
        severity: str | None = None,
        rule_id: str | None = None,
    ) -> tuple[Finding, ...]:
        """Return persisted findings in stable feed order with optional filters."""

        statement = select(FindingRow)
        if student_ref is not None:
            statement = statement.where(FindingRow.student_ref == student_ref)
        if status is not None:
            statement = statement.where(FindingRow.status == status)
        if severity is not None:
            statement = statement.where(FindingRow.severity == severity)
        if rule_id is not None:
            statement = statement.where(FindingRow.rule_id == rule_id)
        statement = statement.order_by(
            FindingRow.detected_on.desc(),
            FindingRow.severity,
            FindingRow.student_ref,
            FindingRow.rule_id,
            FindingRow.id,
        )
        return tuple(_finding(row) for row in (await self._session.scalars(statement)).all())

    async def transition_finding(
        self,
        finding_id: UUID,
        *,
        status: Literal["open", "resolved"],
        actor_ref: str,
        actor_role: AuditActorRole,
        occurred_at: datetime,
    ) -> Finding:
        """Change finding lifecycle state and append its audit event atomically."""

        row = await self._session.get(FindingRow, finding_id)
        if row is None:
            raise FindingNotFoundError(f"finding {finding_id} does not exist")
        if row.status == status:
            raise InvalidFindingTransitionError(f"finding is already {status}")
        previous = row.status
        row.status = status
        row.resolved_at = occurred_at if status == "resolved" else None
        self._session.add(
            _finding_transition_event(
                row,
                previous=previous,
                actor_ref=actor_ref,
                actor_role=actor_role,
                occurred_at=occurred_at,
            )
        )
        await self._session.commit()
        return _finding(row)

    async def record_service_delay_reason(
        self,
        *,
        iep_record_version_id: UUID,
        service_id: UUID,
        reason: str,
        actor_ref: str,
        actor_role: AuditActorRole,
        occurred_at: datetime,
    ) -> None:
        """Record a case-manager-authorized exception with an atomic audit event."""

        _require_case_manager(actor_role)
        normalized_reason = reason.strip()
        if not normalized_reason:
            raise ValueError("service-delay reason cannot be empty")
        approved = await self._session.get(IEPRecordRow, iep_record_version_id)
        if approved is None or not approved.is_current_approved:
            raise ApprovedRecordNotFoundError(
                f"current approved IEP version {iep_record_version_id} does not exist"
            )
        record = IEPRecord.model_validate_json(json.dumps(approved.payload))
        if service_id not in {service.id for service in record.services}:
            raise ServiceDelayReasonNotFoundError(
                f"service {service_id} is not in approved IEP version {iep_record_version_id}"
            )
        statement = select(ServiceDelayReasonRow).where(
            ServiceDelayReasonRow.iep_record_version_id == iep_record_version_id,
            ServiceDelayReasonRow.service_id == service_id,
        )
        row = (await self._session.scalars(statement)).one_or_none()
        previous_reason = None if row is None else row.reason
        previous_active = False if row is None else row.active
        if row is None:
            row = ServiceDelayReasonRow(
                id=uuid4(),
                iep_record_version_id=iep_record_version_id,
                service_id=service_id,
                reason=normalized_reason,
                created_by_ref=actor_ref,
                active=True,
                revoked_at=None,
                revoked_by_ref=None,
            )
            self._session.add(row)
        else:
            row.reason = normalized_reason
            row.created_by_ref = actor_ref
            row.active = True
            row.revoked_at = None
            row.revoked_by_ref = None
        self._session.add(
            _service_delay_reason_event(
                row,
                event_type="service_delay_reason.recorded",
                actor_ref=actor_ref,
                occurred_at=occurred_at,
                previous_reason=previous_reason,
                previous_active=previous_active,
            )
        )
        await self._session.commit()

    async def revoke_service_delay_reason(
        self,
        *,
        iep_record_version_id: UUID,
        service_id: UUID,
        actor_ref: str,
        actor_role: AuditActorRole,
        occurred_at: datetime,
    ) -> None:
        """Revoke a suppression so the next derivation evaluates the delay again."""

        _require_case_manager(actor_role)
        statement = select(ServiceDelayReasonRow).where(
            ServiceDelayReasonRow.iep_record_version_id == iep_record_version_id,
            ServiceDelayReasonRow.service_id == service_id,
            ServiceDelayReasonRow.active.is_(True),
        )
        row = (await self._session.scalars(statement)).one_or_none()
        if row is None:
            raise ServiceDelayReasonNotFoundError(
                f"active reason for service {service_id} does not exist"
            )
        row.active = False
        row.revoked_at = occurred_at
        row.revoked_by_ref = actor_ref
        self._session.add(
            _service_delay_reason_event(
                row,
                event_type="service_delay_reason.revoked",
                actor_ref=actor_ref,
                occurred_at=occurred_at,
                previous_reason=row.reason,
                previous_active=True,
            )
        )
        await self._session.commit()

    async def record_scope_alias(
        self,
        *,
        school_year: str,
        scope: Literal["subject", "context"],
        document_ref: str,
        target_ref: str,
        actor_ref: str,
        actor_role: AuditActorRole,
        occurred_at: datetime,
    ) -> UUID:
        """Create or reactivate a reusable district mapping with administrator audit."""

        if actor_role != "compliance_admin":
            raise InvalidScopeMappingActorError(
                "district scope aliases require a compliance-admin actor"
            )
        normalized_ref = normalize_scope_text(document_ref)
        normalized_target = target_ref.strip()
        if not normalized_ref or not normalized_target:
            raise ValueError("scope alias references cannot be empty")
        statement = select(ScopeReferenceAlias).where(
            ScopeReferenceAlias.school_year == school_year,
            ScopeReferenceAlias.scope == scope,
            ScopeReferenceAlias.normalized_ref == normalized_ref,
            ScopeReferenceAlias.target_ref == normalized_target,
        )
        row = (await self._session.scalars(statement)).one_or_none()
        previous_active = False if row is None else row.active
        if row is None:
            row = ScopeReferenceAlias(
                id=uuid4(),
                school_year=school_year,
                scope=scope,
                document_ref=document_ref,
                normalized_ref=normalized_ref,
                target_ref=normalized_target,
                active=True,
                created_by_ref=actor_ref,
                revoked_at=None,
                revoked_by_ref=None,
            )
            self._session.add(row)
        else:
            row.document_ref = document_ref
            row.active = True
            row.created_by_ref = actor_ref
            row.revoked_at = None
            row.revoked_by_ref = None
        self._session.add(
            _scope_mapping_event(
                row,
                mapping_kind="district_alias",
                event_type="scope_alias.recorded",
                actor_ref=actor_ref,
                actor_role="compliance_admin",
                occurred_at=occurred_at,
                previous_active=previous_active,
            )
        )
        await self._session.commit()
        return row.id

    async def revoke_scope_alias(
        self,
        alias_id: UUID,
        *,
        actor_ref: str,
        actor_role: AuditActorRole,
        occurred_at: datetime,
    ) -> None:
        """Revoke a reusable district alias without deleting its history."""

        if actor_role != "compliance_admin":
            raise InvalidScopeMappingActorError(
                "district scope aliases require a compliance-admin actor"
            )
        row = await self._session.get(ScopeReferenceAlias, alias_id)
        if row is None or not row.active:
            raise ScopeReferenceMappingNotFoundError(f"active scope alias {alias_id} not found")
        row.active = False
        row.revoked_at = occurred_at
        row.revoked_by_ref = actor_ref
        self._session.add(
            _scope_mapping_event(
                row,
                mapping_kind="district_alias",
                event_type="scope_alias.revoked",
                actor_ref=actor_ref,
                actor_role="compliance_admin",
                occurred_at=occurred_at,
                previous_active=True,
            )
        )
        await self._session.commit()

    async def resolve_scope_finding(
        self,
        finding_id: UUID,
        *,
        target_ref: str,
        actor_ref: str,
        actor_role: AuditActorRole,
        occurred_at: datetime,
    ) -> UUID:
        """Map one finding's verbatim scope reference for one approved IEP version."""

        if actor_role != "case_manager":
            raise InvalidScopeMappingActorError(
                "IEP-specific scope resolutions require a case-manager actor"
            )
        finding = await self._session.get(FindingRow, finding_id)
        if (
            finding is None
            or finding.finding_type
            not in {"scope-reference-unresolved", "scope-reference-ambiguous"}
            or finding.iep_record_version_id is None
        ):
            raise ScopeReferenceMappingNotFoundError(
                f"scope resolution finding {finding_id} not found"
            )
        related = finding.related_refs
        accommodation_id = UUID(str(related["accommodation_id"]))
        scope = str(related["scope"])
        document_ref = str(related["scope_ref"])
        normalized_ref = normalize_scope_text(document_ref)
        normalized_target = target_ref.strip()
        if not normalized_target:
            raise ValueError("scope resolution target cannot be empty")
        statement = select(ScopeReferenceResolution).where(
            ScopeReferenceResolution.iep_record_version_id == finding.iep_record_version_id,
            ScopeReferenceResolution.accommodation_id == accommodation_id,
            ScopeReferenceResolution.scope == scope,
            ScopeReferenceResolution.normalized_ref == normalized_ref,
        )
        row = (await self._session.scalars(statement)).one_or_none()
        previous_active = False if row is None else row.active
        previous_target = None if row is None else row.target_ref
        if row is None:
            row = ScopeReferenceResolution(
                id=uuid4(),
                iep_record_version_id=finding.iep_record_version_id,
                accommodation_id=accommodation_id,
                scope=scope,
                document_ref=document_ref,
                normalized_ref=normalized_ref,
                target_ref=normalized_target,
                active=True,
                created_by_ref=actor_ref,
                revoked_at=None,
                revoked_by_ref=None,
            )
            self._session.add(row)
        else:
            row.document_ref = document_ref
            row.target_ref = normalized_target
            row.active = True
            row.created_by_ref = actor_ref
            row.revoked_at = None
            row.revoked_by_ref = None
        self._session.add(
            _scope_mapping_event(
                row,
                mapping_kind="iep_resolution",
                event_type="scope_resolution.recorded",
                actor_ref=actor_ref,
                actor_role="case_manager",
                occurred_at=occurred_at,
                previous_active=previous_active,
                previous_target=previous_target,
            )
        )
        await self._session.commit()
        return row.id

    async def revoke_scope_resolution(
        self,
        resolution_id: UUID,
        *,
        actor_ref: str,
        actor_role: AuditActorRole,
        occurred_at: datetime,
    ) -> None:
        """Revoke a per-IEP resolution so the next derivation reopens its finding."""

        if actor_role != "case_manager":
            raise InvalidScopeMappingActorError(
                "IEP-specific scope resolutions require a case-manager actor"
            )
        row = await self._session.get(ScopeReferenceResolution, resolution_id)
        if row is None or not row.active:
            raise ScopeReferenceMappingNotFoundError(
                f"active scope resolution {resolution_id} not found"
            )
        row.active = False
        row.revoked_at = occurred_at
        row.revoked_by_ref = actor_ref
        self._session.add(
            _scope_mapping_event(
                row,
                mapping_kind="iep_resolution",
                event_type="scope_resolution.revoked",
                actor_ref=actor_ref,
                actor_role="case_manager",
                occurred_at=occurred_at,
                previous_active=True,
                previous_target=row.target_ref,
            )
        )
        await self._session.commit()

    async def derive_district_findings(
        self, *, generated_at: datetime, as_of: date, derivation_run_id: UUID
    ) -> tuple[Finding, ...]:
        """Persist missing-approved-IEP findings for active roster students."""

        roster_statement = (
            select(Student.id, Student.student_ref, Class.school_year)
            .join(Enrollment, Enrollment.student_id == Student.id)
            .join(Class, Class.id == Enrollment.class_id)
            .where(Enrollment.active.is_(True))
            .distinct()
            .order_by(Student.student_ref, Class.school_year)
        )
        roster_rows = tuple((await self._session.execute(roster_statement)).all())
        approved_statement = select(
            IEPRecordRow.student_id, IEPRecordRow.school_year, IEPRecordRow.id
        ).where(IEPRecordRow.is_current_approved.is_(True))
        approved_by_student_year = {
            (student_id, school_year): row_id
            for student_id, school_year, row_id in (
                await self._session.execute(approved_statement)
            ).all()
        }
        findings = derive_district_findings(
            DistrictRuleState(
                students=tuple(
                    RosterStudent(
                        student_ref=student_ref,
                        school_year=school_year,
                        current_approved_iep_version_id=approved_by_student_year.get(
                            (student_id, school_year)
                        ),
                    )
                    for student_id, student_ref, school_year in roster_rows
                ),
                as_of=as_of,
            )
        )
        existing = {
            row.id: row
            for row in (
                await self._session.scalars(
                    select(FindingRow).where(FindingRow.rule_id == "iep-in-effect-start-of-year")
                )
            ).all()
        }
        emitted_ids = {finding.id for finding in findings}
        for finding in findings:
            row = existing.get(finding.id)
            if row is None:
                self._session.add(_finding_row(finding))
                self._session.add(
                    _district_finding_opened_event(finding, generated_at, derivation_run_id)
                )
            elif row.status == "resolved":
                row.status = "open"
                row.resolved_at = None
                _update_finding(row, finding)
                self._session.add(
                    _finding_transition_event(
                        row,
                        previous="resolved",
                        actor_ref="rules-engine",
                        actor_role="system",
                        occurred_at=generated_at,
                        derivation_run_id=derivation_run_id,
                        reason=("The district roster re-derivation found no current approved IEP."),
                    )
                )
        for row in existing.values():
            if row.status == "open" and row.id not in emitted_ids:
                row.status = "resolved"
                row.resolved_at = generated_at
                self._session.add(
                    _finding_transition_event(
                        row,
                        previous="open",
                        actor_ref="rules-engine",
                        actor_role="system",
                        occurred_at=generated_at,
                        derivation_run_id=derivation_run_id,
                        reason=(
                            "The district roster re-derivation now found a current approved IEP."
                        ),
                    )
                )
        await self._session.commit()
        return findings

    async def _load_approved(self, lineage_id: UUID) -> ApprovedRecord:
        row = await get_current_approved_record(self._session, lineage_id)
        if row is None:
            raise ApprovedRecordNotFoundError(
                f"no current approved IEP record exists for lineage {lineage_id}"
            )
        return ApprovedRecord(
            row_id=row.id,
            student_id=row.student_id,
            record=IEPRecord.model_validate_json(json.dumps(row.payload)),
            approved_on=(
                None
                if row.approved_at is None
                else row.approved_at.astimezone(ZoneInfo(get_settings().school_timezone)).date()
            ),
        )

    async def _load_roster(
        self,
        approved: ApprovedRecord,
        *,
        generated_at: datetime,
        as_of: date,
    ) -> RosterSnapshot:
        teacher_statement = (
            select(Class, Teacher, ClassStaff.role)
            .join(Enrollment, Enrollment.class_id == Class.id)
            .join(ClassStaff, ClassStaff.class_id == Class.id)
            .join(Teacher, Teacher.id == ClassStaff.teacher_id)
            .where(
                Enrollment.student_id == approved.student_id,
                Enrollment.school_year == approved.record.school_year,
                Enrollment.active.is_(True),
                ClassStaff.active.is_(True),
            )
            .order_by(Class.class_ref, Teacher.teacher_ref)
        )
        class_people: defaultdict[UUID, list[TeacherAssignment]] = defaultdict(list)
        classes: dict[UUID, Class] = {}
        for classroom, teacher, role in (await self._session.execute(teacher_statement)).all():
            classes[classroom.id] = classroom
            class_people[classroom.id].append(
                TeacherAssignment(teacher_ref=teacher.teacher_ref, role=role)
            )
        roster_classes = tuple(
            RosterClass(
                class_ref=classes[class_id].class_ref,
                subject=classes[class_id].subject,
                teachers=tuple(class_people[class_id]),
            )
            for class_id in sorted(classes, key=lambda value: classes[value].class_ref)
        )
        provider_statement = (
            select(ServiceAssignment.service_id, Provider.provider_ref, Provider.role)
            .join(Provider, Provider.id == ServiceAssignment.provider_id)
            .where(
                ServiceAssignment.iep_record_version_id == approved.row_id,
                ServiceAssignment.active.is_(True),
            )
            .order_by(ServiceAssignment.service_id, Provider.provider_ref)
        )
        providers = tuple(
            ProviderAssignment(
                service_id=service_id,
                provider_ref=provider_ref,
                provider_role=provider_role,
            )
            for service_id, provider_ref, provider_role in (
                await self._session.execute(provider_statement)
            ).all()
        )
        calendar_statement = (
            select(SchoolCalendarDay)
            .where(SchoolCalendarDay.school_year == approved.record.school_year)
            .order_by(SchoolCalendarDay.day)
        )
        calendar_days = tuple(
            CalendarDay(day=row.day, instructional=row.instructional)
            for row in (await self._session.scalars(calendar_statement)).all()
        )
        term_statement = (
            select(SchoolTerm)
            .where(SchoolTerm.school_year == approved.record.school_year)
            .order_by(SchoolTerm.start_on, SchoolTerm.term_ref)
        )
        terms = tuple(
            RuleSchoolTerm(
                term_ref=row.term_ref,
                kind=TermKind(row.kind),
                start_on=row.start_on,
                end_on=row.end_on,
            )
            for row in (await self._session.scalars(term_statement)).all()
        )
        profile_statement = select(StudentComplianceProfile).where(
            StudentComplianceProfile.student_id == approved.student_id,
            StudentComplianceProfile.school_year == approved.record.school_year,
        )
        profile_row = (await self._session.scalars(profile_statement)).one_or_none()
        profile = (
            ComplianceProfile()
            if profile_row is None
            else ComplianceProfile(
                initial_eligibility=profile_row.initial_eligibility,
                eligibility_determined_on=profile_row.eligibility_determined_on,
            )
        )
        service_log_statement = (
            select(ServiceDeliveryLogRow)
            .where(ServiceDeliveryLogRow.iep_record_version_id == approved.row_id)
            .order_by(
                ServiceDeliveryLogRow.delivered_on,
                ServiceDeliveryLogRow.service_id,
                ServiceDeliveryLogRow.id,
            )
        )
        service_logs = tuple(
            ServiceDeliveryLog(
                log_id=row.id,
                service_id=row.service_id,
                delivered_on=row.delivered_on,
                minutes=row.minutes,
                provider_ref=row.provider_ref,
                substitute_for_ref=row.substitute_for_ref,
                makeup_for_week_start=row.makeup_for_week_start,
            )
            for row in (await self._session.scalars(service_log_statement)).all()
        )
        brief_statement = (
            select(Brief, Class.class_ref, Teacher.teacher_ref)
            .join(Class, Class.id == Brief.class_id)
            .join(Teacher, Teacher.id == Brief.teacher_id)
            .where(Brief.iep_record_version_id == approved.row_id)
            .order_by(Class.class_ref, Teacher.teacher_ref, Brief.id)
        )
        school_timezone = ZoneInfo(get_settings().school_timezone)
        briefs = tuple(
            BriefSnapshot(
                brief_id=row.id,
                class_ref=class_ref,
                teacher_ref=teacher_ref,
                status=row.status,
                released_on=(
                    None
                    if row.released_at is None
                    else row.released_at.astimezone(school_timezone).date()
                ),
            )
            for row, class_ref, teacher_ref in (await self._session.execute(brief_statement)).all()
        )
        accommodation_statement = (
            select(ObligationRow)
            .where(
                ObligationRow.iep_record_version_id == approved.row_id,
                ObligationRow.rule_id == "teacher-informed-accommodations",
                ObligationRow.context_kind == "class",
            )
            .order_by(
                ObligationRow.source_ref,
                ObligationRow.context_ref,
                ObligationRow.assignee_ref,
            )
        )
        accommodation_rows = tuple((await self._session.scalars(accommodation_statement)).all())
        accommodation_groups: defaultdict[tuple[UUID, str], list[ObligationRow]] = defaultdict(list)
        for row in accommodation_rows:
            accommodation_groups[(row.source_ref, row.context_ref)].append(row)
        accommodation_classes = tuple(
            AccommodationClassState(
                accommodation_id=accommodation_id,
                class_ref=class_ref,
                obligation_refs=tuple(row.id for row in rows),
                confirmed=all(row.status == "confirmed" for row in rows),
            )
            for (accommodation_id, class_ref), rows in accommodation_groups.items()
        )
        delay_reason_statement = (
            select(ServiceDelayReasonRow)
            .where(
                ServiceDelayReasonRow.iep_record_version_id == approved.row_id,
                ServiceDelayReasonRow.active.is_(True),
            )
            .order_by(ServiceDelayReasonRow.service_id)
        )
        service_delay_reasons = tuple(
            ServiceDelayReason(service_id=row.service_id, reason=row.reason)
            for row in (await self._session.scalars(delay_reason_statement)).all()
        )
        alias_statement = (
            select(ScopeReferenceAlias)
            .where(
                ScopeReferenceAlias.school_year == approved.record.school_year,
                ScopeReferenceAlias.active.is_(True),
            )
            .order_by(
                ScopeReferenceAlias.scope,
                ScopeReferenceAlias.normalized_ref,
                ScopeReferenceAlias.target_ref,
            )
        )
        aliases = tuple(
            ScopeReferenceMapping(
                scope=AccommodationScope(row.scope),
                document_ref=row.document_ref,
                target_ref=row.target_ref,
                kind=ScopeMappingKind.DISTRICT_ALIAS,
            )
            for row in (await self._session.scalars(alias_statement)).all()
        )
        resolution_statement = (
            select(ScopeReferenceResolution)
            .where(
                ScopeReferenceResolution.iep_record_version_id == approved.row_id,
                ScopeReferenceResolution.active.is_(True),
            )
            .order_by(
                ScopeReferenceResolution.accommodation_id,
                ScopeReferenceResolution.scope,
                ScopeReferenceResolution.normalized_ref,
            )
        )
        resolutions = tuple(
            ScopeReferenceMapping(
                scope=AccommodationScope(row.scope),
                document_ref=row.document_ref,
                target_ref=row.target_ref,
                kind=ScopeMappingKind.HUMAN_RESOLUTION,
                accommodation_id=row.accommodation_id,
            )
            for row in (await self._session.scalars(resolution_statement)).all()
        )
        return RosterSnapshot(
            classes=roster_classes,
            providers=providers,
            scope_mappings=(*resolutions, *aliases),
            briefs=briefs,
            accommodation_classes=accommodation_classes,
            service_delay_reasons=service_delay_reasons,
            service_start_delay_school_days=get_settings().service_start_delay_school_days,
            service_logs=service_logs,
            calendar_days=calendar_days,
            terms=terms,
            compliance_profile=profile,
            generated_at=generated_at,
            as_of=as_of,
        )


def _obligation_row(approved: ApprovedRecord, item: DerivedObligation) -> ObligationRow:
    return ObligationRow(
        id=item.id,
        iep_record_version_id=approved.row_id,
        student_id=approved.student_id,
        assignee_kind=item.assignee_kind.value,
        assignee_ref=item.assignee_ref,
        assignee_role=item.assignee_role,
        context_kind=item.context_kind.value,
        context_ref=item.context_ref,
        subject=item.subject,
        source_kind=item.source_kind.value,
        source_ref=item.source_ref,
        scope_provenance=[evidence.model_dump(mode="json") for evidence in item.scope_provenance],
        rule_id=item.rule_id,
        citation=item.citation,
        action_text=item.action_text,
        practice_text=None,
        status="pending",
    )


def _unseen_obligations(
    existing_ids: set[UUID], obligations: tuple[DerivedObligation, ...]
) -> tuple[DerivedObligation, ...]:
    """Return deterministic identities absent from a persistence snapshot."""

    return tuple(item for item in obligations if item.id not in existing_ids)


def _finding_row(item: Finding) -> FindingRow:
    return FindingRow(
        id=item.id,
        iep_record_version_id=item.iep_record_version_id,
        student_ref=item.student_ref,
        rule_id=item.rule_id,
        citation=item.citation,
        finding_type=item.finding_type,
        severity=item.severity.value,
        detected_on=item.detected_on,
        title=item.title,
        detail=item.detail,
        related_refs=item.related_refs,
        measurements=item.measurements,
        status=item.status.value,
        resolved_at=None,
    )


def _update_finding(row: FindingRow, item: Finding) -> None:
    row.severity = item.severity.value
    row.detected_on = item.detected_on
    row.title = item.title
    row.detail = item.detail
    row.related_refs = item.related_refs
    row.measurements = item.measurements


def _finding(row: FindingRow) -> Finding:
    return Finding(
        id=row.id,
        rule_id=row.rule_id,
        citation=row.citation,
        finding_type=row.finding_type,
        severity=FindingSeverity(row.severity),
        student_ref=row.student_ref,
        iep_record_version_id=row.iep_record_version_id,
        detected_on=row.detected_on,
        title=row.title,
        detail=row.detail,
        related_refs=row.related_refs,
        measurements=row.measurements,
        status=FindingStatus(row.status),
    )


def _require_case_manager(actor_role: AuditActorRole) -> None:
    if actor_role != "case_manager":
        raise InvalidServiceDelayReasonActorError(
            "service-delay reasons require a case-manager actor"
        )


def _service_delay_reason_event(
    row: ServiceDelayReasonRow,
    *,
    event_type: str,
    actor_ref: str,
    occurred_at: datetime,
    previous_reason: str | None,
    previous_active: bool,
) -> AuditEvent:
    payload = cast(
        dict[str, JsonValue],
        {
            "summary": (
                "A case manager recorded a documented service-delay reason."
                if row.active
                else "A case manager revoked a documented service-delay reason."
            ),
            "changes": [
                {
                    "field_path": "reason",
                    "previous_value": previous_reason,
                    "new_value": row.reason if row.active else None,
                },
                {
                    "field_path": "active",
                    "previous_value": previous_active,
                    "new_value": row.active,
                },
            ],
            "evidence": [
                {
                    "evidence_type": "service",
                    "evidence_ref": str(row.service_id),
                    "locator": str(row.iep_record_version_id),
                }
            ],
        },
    )
    return AuditEvent(
        id=uuid4(),
        event_type=event_type,
        occurred_at=occurred_at,
        actor_ref=actor_ref,
        actor_role="case_manager",
        subject_type="service_delay_reason",
        subject_ref=str(row.id),
        payload=payload,
        correlation_id=row.iep_record_version_id,
    )


def _scope_mapping_event(
    row: ScopeReferenceAlias | ScopeReferenceResolution,
    *,
    mapping_kind: str,
    event_type: str,
    actor_ref: str,
    actor_role: AuditActorRole,
    occurred_at: datetime,
    previous_active: bool,
    previous_target: str | None = None,
) -> AuditEvent:
    payload = cast(
        dict[str, JsonValue],
        {
            "summary": f"An authorized actor {event_type.replace('.', ' ')}.",
            "changes": [
                {
                    "field_path": "target_ref",
                    "previous_value": previous_target,
                    "new_value": row.target_ref if row.active else None,
                },
                {
                    "field_path": "active",
                    "previous_value": previous_active,
                    "new_value": row.active,
                },
            ],
            "evidence": [
                {
                    "evidence_type": "document",
                    "evidence_ref": row.document_ref,
                    "locator": row.scope,
                }
            ],
        },
    )
    correlation_id = (
        row.iep_record_version_id if isinstance(row, ScopeReferenceResolution) else None
    )
    return AuditEvent(
        id=uuid4(),
        event_type=event_type,
        occurred_at=occurred_at,
        actor_ref=actor_ref,
        actor_role=actor_role,
        subject_type=mapping_kind,
        subject_ref=str(row.id),
        payload=payload,
        correlation_id=correlation_id,
    )


def _deadline_row(item: Deadline) -> ComplianceDeadline:
    return ComplianceDeadline(
        id=item.id,
        iep_record_version_id=item.iep_record_version_id,
        student_ref=item.student_ref,
        rule_id=item.rule_id,
        citation=item.citation,
        source_kind=item.source_kind.value,
        source_ref=item.source_ref,
        legal_due_on=item.legal_due_on,
        action_due_on=item.action_due_on,
        warning_30_on=item.warning_30_on,
        warning_14_on=item.warning_14_on,
        warning_3_on=item.warning_3_on,
        status=item.status.value,
        description=item.description,
    )


def _derived_event(
    approved: ApprovedRecord, item: DerivedObligation, generated_at: datetime
) -> AuditEvent:
    payload = cast(
        dict[str, JsonValue],
        {
            "summary": "Deterministic rules engine created a pending obligation.",
            "changes": [{"field_path": "status", "previous_value": None, "new_value": "pending"}],
            "evidence": [
                {
                    "evidence_type": "rule_citation",
                    "evidence_ref": item.citation,
                    "locator": item.rule_id,
                }
            ],
        },
    )
    return AuditEvent(
        id=uuid4(),
        event_type="obligation.derived",
        occurred_at=generated_at,
        actor_ref="rules-engine",
        actor_role="system",
        subject_type="obligation",
        subject_ref=str(item.id),
        payload=payload,
        correlation_id=approved.row_id,
    )


def _scope_provenance_event(
    row: ObligationRow,
    *,
    previous: list[dict[str, JsonValue]],
    occurred_at: datetime,
    derivation_run_id: UUID,
) -> AuditEvent:
    payload = cast(
        dict[str, JsonValue],
        {
            "summary": "Deterministic scope provenance changed during re-derivation.",
            "derivation_run_id": str(derivation_run_id),
            "changes": [
                {
                    "field_path": "scope_provenance",
                    "previous_value": previous,
                    "new_value": row.scope_provenance,
                }
            ],
            "evidence": [
                {
                    "evidence_type": "rule_citation",
                    "evidence_ref": row.citation,
                    "locator": row.rule_id,
                }
            ],
        },
    )
    return AuditEvent(
        id=uuid4(),
        event_type="obligation.scope_provenance_updated",
        occurred_at=occurred_at,
        actor_ref="rules-engine",
        actor_role="system",
        subject_type="obligation",
        subject_ref=str(row.id),
        payload=payload,
        correlation_id=derivation_run_id,
    )


def _finding_opened_event(
    finding: Finding,
    generated_at: datetime,
    derivation_run_id: UUID,
) -> AuditEvent:
    payload = cast(
        dict[str, JsonValue],
        {
            "summary": finding.detail,
            "derivation_run_id": str(derivation_run_id),
            "changes": [{"field_path": "status", "previous_value": None, "new_value": "open"}],
            "evidence": [
                {
                    "evidence_type": "rule_citation",
                    "evidence_ref": finding.citation,
                    "locator": finding.rule_id,
                }
            ],
        },
    )
    return AuditEvent(
        id=uuid4(),
        event_type="finding.opened",
        occurred_at=generated_at,
        actor_ref="rules-engine",
        actor_role="system",
        subject_type="finding",
        subject_ref=str(finding.id),
        payload=payload,
        correlation_id=derivation_run_id,
    )


def _district_finding_opened_event(
    finding: Finding, generated_at: datetime, derivation_run_id: UUID
) -> AuditEvent:
    payload = cast(
        dict[str, JsonValue],
        {
            "summary": finding.detail,
            "derivation_run_id": str(derivation_run_id),
            "changes": [{"field_path": "status", "previous_value": None, "new_value": "open"}],
            "evidence": [
                {
                    "evidence_type": "rule_citation",
                    "evidence_ref": finding.citation,
                    "locator": finding.rule_id,
                }
            ],
        },
    )
    return AuditEvent(
        id=uuid4(),
        event_type="finding.opened",
        occurred_at=generated_at,
        actor_ref="rules-engine",
        actor_role="system",
        subject_type="finding",
        subject_ref=str(finding.id),
        payload=payload,
        correlation_id=derivation_run_id,
    )


def _finding_transition_event(
    row: FindingRow,
    *,
    previous: str,
    actor_ref: str,
    actor_role: AuditActorRole,
    occurred_at: datetime,
    derivation_run_id: UUID | None = None,
    reason: str | None = None,
) -> AuditEvent:
    payload = cast(
        dict[str, JsonValue],
        {
            "summary": reason or f"Finding status changed from {previous} to {row.status}.",
            "derivation_run_id": (None if derivation_run_id is None else str(derivation_run_id)),
            "changes": [
                {
                    "field_path": "status",
                    "previous_value": previous,
                    "new_value": row.status,
                }
            ],
            "evidence": [
                {
                    "evidence_type": "rule_citation",
                    "evidence_ref": row.citation,
                    "locator": row.rule_id,
                }
            ],
        },
    )
    return AuditEvent(
        id=uuid4(),
        event_type=f"finding.{row.status}",
        occurred_at=occurred_at,
        actor_ref=actor_ref,
        actor_role=actor_role,
        subject_type="finding",
        subject_ref=str(row.id),
        payload=payload,
        correlation_id=derivation_run_id or row.iep_record_version_id,
    )


def _deadline_event(
    approved: ApprovedRecord, deadline: Deadline, occurred_at: datetime
) -> AuditEvent:
    payload = cast(
        dict[str, JsonValue],
        {
            "summary": deadline.description,
            "changes": [
                {
                    "field_path": "status",
                    "previous_value": None,
                    "new_value": deadline.status.value,
                }
            ],
            "evidence": [
                {
                    "evidence_type": "rule_citation",
                    "evidence_ref": deadline.citation,
                    "locator": deadline.rule_id,
                }
            ],
        },
    )
    return AuditEvent(
        id=uuid4(),
        event_type="deadline.scheduled",
        occurred_at=occurred_at,
        actor_ref="rules-engine",
        actor_role="system",
        subject_type="compliance_deadline",
        subject_ref=str(deadline.id),
        payload=payload,
        correlation_id=approved.row_id,
    )


def _sync_deadline(
    row: ComplianceDeadline, deadline: Deadline, occurred_at: datetime
) -> AuditEvent | None:
    tracked = {
        "legal_due_on": deadline.legal_due_on,
        "action_due_on": deadline.action_due_on,
        "warning_30_on": deadline.warning_30_on,
        "warning_14_on": deadline.warning_14_on,
        "warning_3_on": deadline.warning_3_on,
        "status": deadline.status.value,
    }
    changes: list[dict[str, JsonValue]] = []
    for field_name, new_value in tracked.items():
        previous = getattr(row, field_name)
        if previous != new_value:
            changes.append(
                {
                    "field_path": field_name,
                    "previous_value": (
                        previous.isoformat() if isinstance(previous, date) else previous
                    ),
                    "new_value": new_value.isoformat()
                    if isinstance(new_value, date)
                    else new_value,
                }
            )
            setattr(row, field_name, new_value)
    if not changes:
        return None
    payload = cast(
        dict[str, JsonValue],
        {
            "summary": "Deterministic deadline state was recalculated.",
            "changes": changes,
            "evidence": [
                {
                    "evidence_type": "rule_citation",
                    "evidence_ref": deadline.citation,
                    "locator": deadline.rule_id,
                }
            ],
        },
    )
    return AuditEvent(
        id=uuid4(),
        event_type="deadline.recalculated",
        occurred_at=occurred_at,
        actor_ref="rules-engine",
        actor_role="system",
        subject_type="compliance_deadline",
        subject_ref=str(deadline.id),
        payload=payload,
        correlation_id=deadline.iep_record_version_id,
    )


def _transition_event(
    row: ObligationRow,
    *,
    previous: str,
    actor_ref: str,
    actor_role: AuditActorRole,
    occurred_at: datetime,
) -> AuditEvent:
    payload = cast(
        dict[str, JsonValue],
        {
            "summary": f"Obligation status changed from {previous} to {row.status}.",
            "changes": [
                {"field_path": "status", "previous_value": previous, "new_value": row.status}
            ],
            "evidence": [
                {
                    "evidence_type": "rule_citation",
                    "evidence_ref": row.citation,
                    "locator": row.rule_id,
                }
            ],
        },
    )
    return AuditEvent(
        id=uuid4(),
        event_type=f"obligation.{row.status}",
        occurred_at=occurred_at,
        actor_ref=actor_ref,
        actor_role=actor_role,
        subject_type="obligation",
        subject_ref=str(row.id),
        payload=payload,
        correlation_id=row.iep_record_version_id,
    )


def _obligation_set(
    key: tuple[str, str, str, str, str, str | None],
    rows: list[ObligationRow],
    approved: ApprovedRecord,
) -> ObligationSet:
    assignee_kind, assignee_ref, assignee_role, context_kind, context_ref, subject = key
    generated_at = min(row.created_at for row in rows)
    return ObligationSet(
        assignee_kind=ContractAssigneeKind(assignee_kind),
        assignee_ref=assignee_ref,
        assignee_role=assignee_role,
        context_kind=ObligationContextKind(context_kind),
        context_ref=context_ref,
        subject=subject,
        generated_at=generated_at,
        rules_version=RULES_VERSION,
        obligations=[
            ContractObligation(
                id=row.id,
                student_ref=approved.record.student_ref,
                source_kind=ObligationSourceKind(row.source_kind),
                source_ref=row.source_ref,
                scope_provenance=_read_scope_provenance(row.scope_provenance),
                rule_id=row.rule_id,
                citation=row.citation,
                action_text=row.action_text,
                practice_text=row.practice_text,
                status=ObligationStatus(row.status),
                confirmed_at=row.confirmed_at,
                flag_reason=row.flag_reason,
            )
            for row in rows
        ],
    )


def _read_scope_provenance(
    values: list[dict[str, JsonValue]],
) -> list[ObligationScopeProvenance]:
    """Restore JSON-backed scope values to the strict contract enum."""

    return [
        ObligationScopeProvenance.model_validate(
            {**value, "scope": AccommodationScope(str(value["scope"]))}
        )
        for value in values
    ]
