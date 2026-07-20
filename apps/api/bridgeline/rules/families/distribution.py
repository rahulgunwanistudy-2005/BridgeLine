"""IDEA obligation distribution rules."""

from __future__ import annotations

from uuid import UUID

from bridgeline.rules.families.gaps import (
    partial_confirmation_findings,
    unconfirmed_brief_findings,
)
from bridgeline.rules.scope_resolution import normalize_scope_text, resolve_scope
from bridgeline.rules.types import (
    ApprovedRecord,
    AssigneeKind,
    ContextKind,
    Deadline,
    DerivedObligation,
    Finding,
    FindingSeverity,
    ProviderAssignment,
    RosterSnapshot,
    RuleState,
    ScopeProvenance,
    SourceKind,
    finding_id,
    obligation_id,
)


class TeacherAccessRule:
    """Distribute IEP access to every responsible teacher and provider."""

    id = "teacher-access"
    citation = "34 CFR §300.323(d)(1)"
    description = (
        "The public agency must ensure the child's IEP is accessible to each regular education "
        "teacher, special education teacher, related services provider, and any other service "
        "provider responsible for its implementation."
    )

    def derive(
        self, record: ApprovedRecord, roster: RosterSnapshot
    ) -> tuple[DerivedObligation, ...]:
        assignees = {
            (AssigneeKind.TEACHER, teacher.teacher_ref, teacher.role)
            for classroom in roster.classes
            for teacher in classroom.teachers
        }
        assignees.update(
            (AssigneeKind.PROVIDER, provider.provider_ref, provider.provider_role)
            for provider in roster.providers
        )
        return tuple(
            _obligation(
                record,
                rule=self,
                assignee_kind=kind,
                assignee_ref=ref,
                assignee_role=role,
                context_kind=ContextKind.STUDENT,
                context_ref=record.record.student_ref,
                subject=None,
                source_kind=SourceKind.IEP_RECORD,
                source_ref=record.row_id,
                action_text="Maintain access to this student's current approved IEP.",
            )
            for kind, ref, role in sorted(assignees, key=lambda item: (item[0].value, item[1]))
        )

    def check(self, state: RuleState) -> tuple[Finding, ...]:
        return ()

    def derive_deadlines(
        self, record: ApprovedRecord, roster: RosterSnapshot
    ) -> tuple[Deadline, ...]:
        return ()


class TeacherResponsibilitiesRule:
    """Inform each assignee of specific implementation responsibilities."""

    id = "teacher-informed-responsibilities"
    citation = "34 CFR §300.323(d)(2)(i)"
    description = (
        "Each teacher and provider described in (d)(1) must be informed of his or her specific "
        "responsibilities related to implementing the child's IEP."
    )

    def derive(
        self, record: ApprovedRecord, roster: RosterSnapshot
    ) -> tuple[DerivedObligation, ...]:
        teacher_obligations = (
            _obligation(
                record,
                rule=self,
                assignee_kind=AssigneeKind.TEACHER,
                assignee_ref=teacher.teacher_ref,
                assignee_role=teacher.role,
                context_kind=ContextKind.CLASS,
                context_ref=classroom.class_ref,
                subject=classroom.subject,
                source_kind=SourceKind.IEP_RECORD,
                source_ref=record.row_id,
                action_text=(
                    f"Implement this student's IEP responsibilities in {classroom.subject}."
                ),
            )
            for classroom in roster.classes
            for teacher in classroom.teachers
        )
        provider_obligations = (
            _provider_responsibility(record, self, provider)
            for provider in roster.providers
            if _service_exists(record, provider.service_id)
        )
        return (*teacher_obligations, *provider_obligations)

    def check(self, state: RuleState) -> tuple[Finding, ...]:
        assigned = {assignment.service_id for assignment in state.roster.providers}
        provider_findings = tuple(
            Finding(
                id=finding_id(
                    state.approved,
                    rule_id=self.id,
                    finding_type="service-provider-unassigned",
                    ref=str(service.id),
                ),
                rule_id=self.id,
                citation=self.citation,
                finding_type="service-provider-unassigned",
                severity=FindingSeverity.WARNING,
                student_ref=state.approved.record.student_ref,
                iep_record_version_id=state.approved.row_id,
                detected_on=state.roster.as_of,
                title=f"No provider assigned for {service.type}",
                detail=(
                    f"{service.type} requires a {service.provider_role}, but no provider-of-record "
                    "is assigned."
                ),
                related_refs={"service_id": str(service.id)},
                measurements={},
            )
            for service in state.approved.record.services
            if service.id not in assigned
        )
        return provider_findings + unconfirmed_brief_findings(
            state, rule_id=self.id, citation=self.citation
        )

    def derive_deadlines(
        self, record: ApprovedRecord, roster: RosterSnapshot
    ) -> tuple[Deadline, ...]:
        return ()


class TeacherAccommodationsRule:
    """Distribute exact approved accommodation text to applicable classes."""

    id = "teacher-informed-accommodations"
    citation = "34 CFR §300.323(d)(2)(ii)"
    description = (
        "Each teacher and provider described in (d)(1) must be informed of the specific "
        "accommodations, modifications, and supports that must be provided for the child in "
        "accordance with the IEP."
    )

    def derive(
        self, record: ApprovedRecord, roster: RosterSnapshot
    ) -> tuple[DerivedObligation, ...]:
        return tuple(
            _obligation(
                record,
                rule=self,
                assignee_kind=AssigneeKind.TEACHER,
                assignee_ref=teacher.teacher_ref,
                assignee_role=teacher.role,
                context_kind=ContextKind.CLASS,
                context_ref=classroom.class_ref,
                subject=classroom.subject,
                source_kind=SourceKind.ACCOMMODATION,
                source_ref=accommodation.id,
                scope_provenance=resolved.provenance,
                action_text=accommodation.text,
            )
            for accommodation in record.record.accommodations
            for resolution in (resolve_scope(accommodation, roster),)
            for resolved in resolution.classes
            for classroom in (resolved.classroom,)
            for teacher in classroom.teachers
        )

    def check(self, state: RuleState) -> tuple[Finding, ...]:
        return (
            *_scope_findings(state, rule_id=self.id, citation=self.citation),
            *partial_confirmation_findings(state, rule_id=self.id, citation=self.citation),
        )

    def derive_deadlines(
        self, record: ApprovedRecord, roster: RosterSnapshot
    ) -> tuple[Deadline, ...]:
        return ()


def _provider_responsibility(
    record: ApprovedRecord,
    rule: TeacherResponsibilitiesRule,
    provider: ProviderAssignment,
) -> DerivedObligation:
    service = next(item for item in record.record.services if item.id == provider.service_id)
    return _obligation(
        record,
        rule=rule,
        assignee_kind=AssigneeKind.PROVIDER,
        assignee_ref=provider.provider_ref,
        assignee_role=provider.provider_role,
        context_kind=ContextKind.SERVICE,
        context_ref=str(service.id),
        subject=None,
        source_kind=SourceKind.SERVICE,
        source_ref=service.id,
        action_text=f"Deliver {service.type}: {service.frequency}.",
    )


def _service_exists(record: ApprovedRecord, service_id: object) -> bool:
    return any(service.id == service_id for service in record.record.services)


def _scope_findings(state: RuleState, *, rule_id: str, citation: str) -> tuple[Finding, ...]:
    return tuple(
        Finding(
            id=finding_id(
                state.approved,
                rule_id=rule_id,
                finding_type=issue.finding_type,
                ref=(
                    f"{accommodation.id}|{issue.reference.scope.value}|"
                    f"{normalize_scope_text(issue.reference.ref)}"
                ),
            ),
            rule_id=rule_id,
            citation=citation,
            finding_type=issue.finding_type,
            severity=FindingSeverity.WARNING,
            student_ref=state.approved.record.student_ref,
            iep_record_version_id=state.approved.row_id,
            detected_on=state.roster.as_of,
            title=f'Scope needs review: "{issue.reference.ref}"',
            detail=issue.detail,
            related_refs={
                "accommodation_id": str(accommodation.id),
                "scope": issue.reference.scope.value,
                "scope_ref": issue.reference.ref,
                "source_page": issue.reference.source_page,
                "source_quote": issue.reference.source_quote,
                "confidence": issue.reference.confidence,
            },
            measurements={},
        )
        for accommodation in state.approved.record.accommodations
        for issue in resolve_scope(accommodation, state.roster).issues
    )


def _obligation(
    record: ApprovedRecord,
    *,
    rule: TeacherAccessRule | TeacherResponsibilitiesRule | TeacherAccommodationsRule,
    assignee_kind: AssigneeKind,
    assignee_ref: str,
    assignee_role: str,
    context_kind: ContextKind,
    context_ref: str,
    subject: str | None,
    source_kind: SourceKind,
    source_ref: UUID,
    action_text: str,
    scope_provenance: tuple[ScopeProvenance, ...] = (),
) -> DerivedObligation:
    return DerivedObligation(
        id=obligation_id(
            record,
            rule_id=rule.id,
            source_kind=source_kind,
            source_ref=source_ref,
            assignee_kind=assignee_kind,
            assignee_ref=assignee_ref,
            context_kind=context_kind,
            context_ref=context_ref,
        ),
        student_ref=record.record.student_ref,
        assignee_kind=assignee_kind,
        assignee_ref=assignee_ref,
        assignee_role=assignee_role,
        context_kind=context_kind,
        context_ref=context_ref,
        subject=subject,
        source_kind=source_kind,
        source_ref=source_ref,
        scope_provenance=scope_provenance,
        rule_id=rule.id,
        citation=rule.citation,
        action_text=action_text,
    )
