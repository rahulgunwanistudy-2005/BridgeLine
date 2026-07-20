"""Deterministic implementation-gap checks."""

from __future__ import annotations

from bridgeline.rules.types import (
    ApprovedRecord,
    Deadline,
    DerivedObligation,
    DistrictRuleState,
    Finding,
    FindingSeverity,
    RosterSnapshot,
    RuleState,
    district_finding_id,
    finding_id,
)

BRIEF_CONFIRMATION_SCHOOL_DAYS = 3


def unconfirmed_brief_findings(
    state: RuleState, *, rule_id: str, citation: str
) -> tuple[Finding, ...]:
    """Find released briefs still unconfirmed after three instructional days."""

    findings: list[Finding] = []
    for brief in state.roster.briefs:
        if brief.status != "released" or brief.released_on is None:
            continue
        elapsed = sum(
            day.instructional
            for day in state.roster.calendar_days
            if brief.released_on < day.day <= state.roster.as_of
        )
        if elapsed < BRIEF_CONFIRMATION_SCHOOL_DAYS:
            continue
        findings.append(
            Finding(
                id=finding_id(
                    state.approved,
                    rule_id=rule_id,
                    finding_type="brief-unconfirmed",
                    ref=str(brief.brief_id),
                ),
                rule_id=rule_id,
                citation=citation,
                finding_type="brief-unconfirmed",
                severity=FindingSeverity.WARNING,
                student_ref=state.approved.record.student_ref,
                iep_record_version_id=state.approved.row_id,
                detected_on=state.roster.as_of,
                title=f"Brief remains unconfirmed for {brief.class_ref}",
                detail=(
                    f"The brief released to {brief.teacher_ref} remains unconfirmed after "
                    f"{elapsed} school days."
                ),
                related_refs={
                    "brief_id": str(brief.brief_id),
                    "class_ref": brief.class_ref,
                    "teacher_ref": brief.teacher_ref,
                },
                measurements={"delay_days": elapsed},
            )
        )
    return tuple(findings)


def partial_confirmation_findings(
    state: RuleState, *, rule_id: str, citation: str
) -> tuple[Finding, ...]:
    """Find accommodations confirmed in only a subset of applicable classes."""

    findings: list[Finding] = []
    for accommodation in state.approved.record.accommodations:
        class_states = tuple(
            item
            for item in state.roster.accommodation_classes
            if item.accommodation_id == accommodation.id
        )
        total = len(class_states)
        confirmed = sum(item.confirmed for item in class_states)
        if confirmed == 0 or confirmed == total:
            continue
        remaining = total - confirmed
        message = (
            f"{accommodation.text} is confirmed in {confirmed} of {total} classes; "
            f"{remaining} classes remain unconfirmed."
        )
        findings.append(
            Finding(
                id=finding_id(
                    state.approved,
                    rule_id=rule_id,
                    finding_type="accommodation-partially-confirmed",
                    ref=str(accommodation.id),
                ),
                rule_id=rule_id,
                citation=citation,
                finding_type="accommodation-partially-confirmed",
                severity=FindingSeverity.CRITICAL,
                student_ref=state.approved.record.student_ref,
                iep_record_version_id=state.approved.row_id,
                detected_on=state.roster.as_of,
                title=message,
                detail=message,
                related_refs={
                    "accommodation_id": str(accommodation.id),
                    "class_refs": [item.class_ref for item in class_states],
                    "obligation_refs": [
                        str(ref) for item in class_states for ref in item.obligation_refs
                    ],
                },
                measurements={
                    "confirmed_classes": confirmed,
                    "total_classes": total,
                    "unconfirmed_classes": remaining,
                },
            )
        )
    return tuple(findings)


class ServicesWithoutDelayRule:
    """Apply the district's documented operational start-delay threshold."""

    id = "services-without-delay"
    citation = "34 CFR §300.323(c)(2)"
    description = (
        "As soon as possible following development of the IEP, special education and related "
        "services must be made available to the child in accordance with the child's IEP."
    )

    def derive(
        self, record: ApprovedRecord, roster: RosterSnapshot
    ) -> tuple[DerivedObligation, ...]:
        return ()

    def derive_deadlines(
        self, record: ApprovedRecord, roster: RosterSnapshot
    ) -> tuple[Deadline, ...]:
        return ()

    def check(self, state: RuleState) -> tuple[Finding, ...]:
        if state.approved.approved_on is None:
            return ()
        documented = {item.service_id for item in state.roster.service_delay_reasons}
        findings: list[Finding] = []
        for service in state.approved.record.services:
            if service.start is None or service.id in documented:
                continue
            delay_days = sum(
                day.instructional
                for day in state.roster.calendar_days
                if state.approved.approved_on < day.day < service.start
            )
            threshold = state.roster.service_start_delay_school_days
            if delay_days <= threshold:
                continue
            findings.append(
                Finding(
                    id=finding_id(
                        state.approved,
                        rule_id=self.id,
                        finding_type="service-start-delay",
                        ref=str(service.id),
                    ),
                    rule_id=self.id,
                    citation=self.citation,
                    finding_type="service-start-delay",
                    severity=FindingSeverity.WARNING,
                    student_ref=state.approved.record.student_ref,
                    iep_record_version_id=state.approved.row_id,
                    detected_on=state.roster.as_of,
                    title=f"{service.type} starts after the district operational threshold",
                    detail=(
                        f"{service.type} starts {delay_days} school days after IEP approval; "
                        f"district policy is {threshold} school days."
                    ),
                    related_refs={"service_id": str(service.id)},
                    measurements={
                        "delay_days": delay_days,
                        "operational_policy_school_days": threshold,
                    },
                )
            )
        return tuple(findings)


class IEPInEffectRule:
    """Check active district roster students for a current approved IEP."""

    id = "iep-in-effect-start-of-year"
    citation = "34 CFR §300.323(a)"
    description = (
        "At the beginning of each school year, the public agency must have an IEP in effect for "
        "each child with a disability within its jurisdiction."
    )

    def derive(
        self, record: ApprovedRecord, roster: RosterSnapshot
    ) -> tuple[DerivedObligation, ...]:
        return ()

    def derive_deadlines(
        self, record: ApprovedRecord, roster: RosterSnapshot
    ) -> tuple[Deadline, ...]:
        return ()

    def check(self, state: RuleState) -> tuple[Finding, ...]:
        return ()

    def check_district(self, state: DistrictRuleState) -> tuple[Finding, ...]:
        return tuple(
            Finding(
                id=district_finding_id(
                    rule_id=self.id,
                    finding_type="current-approved-iep-missing",
                    ref=f"{student.student_ref}:{student.school_year}",
                ),
                rule_id=self.id,
                citation=self.citation,
                finding_type="current-approved-iep-missing",
                severity=FindingSeverity.CRITICAL,
                student_ref=student.student_ref,
                iep_record_version_id=None,
                detected_on=state.as_of,
                title="No current approved IEP is in effect",
                detail=(
                    f"{student.student_ref} is actively enrolled for {student.school_year} but "
                    "has no current approved IEP version on file."
                ),
                related_refs={"roster_entry": student.student_ref},
                measurements={},
            )
            for student in state.students
            if student.current_approved_iep_version_id is None
        )
