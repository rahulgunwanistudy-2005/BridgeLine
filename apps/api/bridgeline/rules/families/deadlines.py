"""Initial, annual, triennial, and progress-report deadline rules."""

from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID

from bridgeline.rules.calendar import (
    CalendarCoverageError,
    UnsupportedCadenceError,
    deadline_status,
    next_cadence_date,
    parse_progress_cadence,
    previous_instructional_day,
    warning_date,
)
from bridgeline.rules.types import (
    ApprovedRecord,
    Deadline,
    DerivedObligation,
    Finding,
    FindingSeverity,
    RosterSnapshot,
    RuleState,
    SourceKind,
    deadline_id,
    finding_id,
)


class InitialIEPMeetingRule:
    """Schedule the one-time initial IEP meeting clock."""

    id = "initial-iep-meeting-30-days"
    citation = "34 CFR §300.323(c)(1)"
    description = (
        "A meeting to develop an IEP for a child must be conducted within 30 days of a "
        "determination that the child needs special education and related services."
    )

    def derive(
        self, record: ApprovedRecord, roster: RosterSnapshot
    ) -> tuple[DerivedObligation, ...]:
        return ()

    def derive_deadlines(
        self, record: ApprovedRecord, roster: RosterSnapshot
    ) -> tuple[Deadline, ...]:
        profile = roster.compliance_profile
        if not profile.initial_eligibility or profile.eligibility_determined_on is None:
            return ()
        legal_due_on = profile.eligibility_determined_on + timedelta(days=30)
        deadline = _deadline(
            record,
            roster,
            rule_id=self.id,
            citation=self.citation,
            source_kind=SourceKind.IEP_RECORD,
            source_ref=record.row_id,
            legal_due_on=legal_due_on,
            description="Conduct the initial IEP meeting.",
        )
        return () if deadline is None else (deadline,)

    def check(self, state: RuleState) -> tuple[Finding, ...]:
        profile = state.roster.compliance_profile
        if not profile.initial_eligibility:
            return ()
        if profile.eligibility_determined_on is None:
            return (
                _input_finding(
                    state,
                    rule_id=self.id,
                    citation=self.citation,
                    finding_type="eligibility-date-missing",
                    ref=state.approved.record.student_ref,
                    detail=(
                        "Initial eligibility is recorded, but its determination date is missing."
                    ),
                ),
            )
        if not self.derive_deadlines(state.approved, state.roster):
            return (_calendar_finding(state, self.id, self.citation, str(state.approved.row_id)),)
        return ()


class AnnualReviewRule:
    """Schedule the approved annual-review deadline."""

    id = "annual-review"
    citation = "34 CFR §300.324(b)(1)(i)"
    description = (
        "The public agency must ensure the IEP Team reviews the child's IEP periodically, but "
        "not less than annually, to determine whether the annual goals are being achieved."
    )

    def derive(
        self, record: ApprovedRecord, roster: RosterSnapshot
    ) -> tuple[DerivedObligation, ...]:
        return ()

    def derive_deadlines(
        self, record: ApprovedRecord, roster: RosterSnapshot
    ) -> tuple[Deadline, ...]:
        legal_due_on = record.record.dates.annual_review
        if legal_due_on is None:
            return ()
        deadline = _deadline(
            record,
            roster,
            rule_id=self.id,
            citation=self.citation,
            source_kind=SourceKind.IEP_RECORD,
            source_ref=record.row_id,
            legal_due_on=legal_due_on,
            description="Complete the annual IEP review.",
        )
        return () if deadline is None else (deadline,)

    def check(self, state: RuleState) -> tuple[Finding, ...]:
        if state.approved.record.dates.annual_review is None:
            return (
                _input_finding(
                    state,
                    rule_id=self.id,
                    citation=self.citation,
                    finding_type="annual-review-date-missing",
                    ref=str(state.approved.row_id),
                    detail="The approved IEP has no annual-review date.",
                ),
            )
        if not self.derive_deadlines(state.approved, state.roster):
            return (_calendar_finding(state, self.id, self.citation, str(state.approved.row_id)),)
        return ()


class TriennialReevaluationRule:
    """Schedule the approved triennial-reevaluation deadline."""

    id = "triennial-reevaluation"
    citation = "34 CFR §300.303(b)(2)"
    description = (
        "A reevaluation must occur at least once every 3 years, unless the parent and the "
        "public agency agree that a reevaluation is unnecessary."
    )

    def derive(
        self, record: ApprovedRecord, roster: RosterSnapshot
    ) -> tuple[DerivedObligation, ...]:
        return ()

    def derive_deadlines(
        self, record: ApprovedRecord, roster: RosterSnapshot
    ) -> tuple[Deadline, ...]:
        legal_due_on = record.record.dates.triennial_reeval
        if legal_due_on is None:
            return ()
        deadline = _deadline(
            record,
            roster,
            rule_id=self.id,
            citation=self.citation,
            source_kind=SourceKind.IEP_RECORD,
            source_ref=record.row_id,
            legal_due_on=legal_due_on,
            description="Complete the triennial reevaluation.",
        )
        return () if deadline is None else (deadline,)

    def check(self, state: RuleState) -> tuple[Finding, ...]:
        if state.approved.record.dates.triennial_reeval is None:
            return (
                _input_finding(
                    state,
                    rule_id=self.id,
                    citation=self.citation,
                    finding_type="triennial-reevaluation-date-missing",
                    ref=str(state.approved.row_id),
                    detail="The approved IEP has no triennial-reevaluation deadline.",
                ),
            )
        if not self.derive_deadlines(state.approved, state.roster):
            return (_calendar_finding(state, self.id, self.citation, str(state.approved.row_id)),)
        return ()


class ProgressReportCadenceRule:
    """Schedule each annual goal's next progress report."""

    id = "progress-report-cadence"
    citation = "34 CFR §300.320(a)(3)"
    description = (
        "The IEP must include a description of how the child's progress toward meeting annual "
        "goals will be measured, and when periodic progress reports will be provided."
    )

    def derive(
        self, record: ApprovedRecord, roster: RosterSnapshot
    ) -> tuple[DerivedObligation, ...]:
        return ()

    def derive_deadlines(
        self, record: ApprovedRecord, roster: RosterSnapshot
    ) -> tuple[Deadline, ...]:
        last_report_on = record.record.dates.last_progress_report
        if last_report_on is None:
            return ()
        deadlines: list[Deadline] = []
        for goal in record.record.goals:
            try:
                cadence = parse_progress_cadence(goal.progress_cadence)
                legal_due_on = next_cadence_date(last_report_on, cadence, roster.terms)
            except (UnsupportedCadenceError, CalendarCoverageError):
                continue
            deadline = _deadline(
                record,
                roster,
                rule_id=self.id,
                citation=self.citation,
                source_kind=SourceKind.GOAL,
                source_ref=goal.id,
                legal_due_on=legal_due_on,
                description=f"Provide a progress report for goal {goal.id}.",
            )
            if deadline is not None:
                deadlines.append(deadline)
        return tuple(deadlines)

    def check(self, state: RuleState) -> tuple[Finding, ...]:
        last_report_on = state.approved.record.dates.last_progress_report
        if last_report_on is None:
            return (
                _input_finding(
                    state,
                    rule_id=self.id,
                    citation=self.citation,
                    finding_type="last-progress-report-date-missing",
                    ref=str(state.approved.row_id),
                    detail="The approved IEP has no last progress-report date.",
                ),
            )
        findings: list[Finding] = []
        for goal in state.approved.record.goals:
            try:
                cadence = parse_progress_cadence(goal.progress_cadence)
                legal_due_on = next_cadence_date(last_report_on, cadence, state.roster.terms)
            except UnsupportedCadenceError:
                findings.append(
                    _input_finding(
                        state,
                        rule_id=self.id,
                        citation=self.citation,
                        finding_type="progress-cadence-unsupported",
                        ref=str(goal.id),
                        detail=f"Unsupported progress cadence: {goal.progress_cadence!r}.",
                    )
                )
                continue
            except CalendarCoverageError:
                findings.append(_calendar_finding(state, self.id, self.citation, str(goal.id)))
                continue
            try:
                _resolve_dates(legal_due_on, state.roster)
            except CalendarCoverageError:
                findings.append(_calendar_finding(state, self.id, self.citation, str(goal.id)))
        return tuple(findings)


def _deadline(
    record: ApprovedRecord,
    roster: RosterSnapshot,
    *,
    rule_id: str,
    citation: str,
    source_kind: SourceKind,
    source_ref: UUID,
    legal_due_on: date,
    description: str,
) -> Deadline | None:
    try:
        action_on, warning_30, warning_14, warning_3 = _resolve_dates(legal_due_on, roster)
    except CalendarCoverageError:
        return None
    return Deadline(
        id=deadline_id(record, rule_id=rule_id, source_ref=source_ref),
        rule_id=rule_id,
        citation=citation,
        student_ref=record.record.student_ref,
        iep_record_version_id=record.row_id,
        source_kind=source_kind,
        source_ref=source_ref,
        legal_due_on=legal_due_on,
        action_due_on=action_on,
        warning_30_on=warning_30,
        warning_14_on=warning_14,
        warning_3_on=warning_3,
        status=deadline_status(legal_due_on, roster.as_of),
        description=description,
    )


def _resolve_dates(legal_due_on: date, roster: RosterSnapshot) -> tuple[date, date, date, date]:
    return (
        previous_instructional_day(legal_due_on, roster.calendar_days),
        warning_date(legal_due_on, 30, roster.calendar_days),
        warning_date(legal_due_on, 14, roster.calendar_days),
        warning_date(legal_due_on, 3, roster.calendar_days),
    )


def _input_finding(
    state: RuleState,
    *,
    rule_id: str,
    citation: str,
    finding_type: str,
    ref: str,
    detail: str,
) -> Finding:
    return Finding(
        id=finding_id(state.approved, rule_id=rule_id, finding_type=finding_type, ref=ref),
        rule_id=rule_id,
        citation=citation,
        finding_type=finding_type,
        severity=FindingSeverity.WARNING,
        student_ref=state.approved.record.student_ref,
        iep_record_version_id=state.approved.row_id,
        detected_on=state.roster.as_of,
        title="Deadline input requires review",
        detail=detail,
        related_refs={"source_ref": ref},
        measurements={},
    )


def _calendar_finding(state: RuleState, rule_id: str, citation: str, ref: str) -> Finding:
    return _input_finding(
        state,
        rule_id=rule_id,
        citation=citation,
        finding_type="calendar-coverage-missing",
        ref=ref,
        detail="The school calendar does not cover every required deadline and warning date.",
    )
