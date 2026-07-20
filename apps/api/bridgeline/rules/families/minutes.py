"""Deterministic weekly service-minute accounting."""

from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID

from bridgeline.rules.types import (
    ApprovedRecord,
    Deadline,
    DerivedObligation,
    Finding,
    FindingSeverity,
    RosterSnapshot,
    RuleState,
    TermKind,
    finding_id,
)


class ServicesStatementRule:
    """Compare approved weekly service minutes with logged delivery."""

    id = "services-statement"
    citation = "34 CFR §300.320(a)(4)"
    description = (
        "The IEP must include a statement of the special education and related services, "
        "supplementary aids and services, and program modifications to be provided, based on "
        "peer-reviewed research to the extent practicable."
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
        service_ids = {service.id for service in state.approved.record.services}
        findings = [
            _input_finding(
                state,
                finding_type="service-log-unknown-service",
                ref=str(log.log_id),
                detail=f"Service log {log.log_id} references an unknown approved service.",
            )
            for log in state.roster.service_logs
            if log.service_id not in service_ids
        ]
        for service in state.approved.record.services:
            if service.start is None or service.end is None:
                findings.append(
                    _input_finding(
                        state,
                        finding_type="service-dates-missing",
                        ref=str(service.id),
                        detail=f"{service.type} has no complete school-local service date range.",
                    )
                )
                continue
            service_logs = tuple(
                log
                for log in state.roster.service_logs
                if log.service_id == service.id and log.delivered_on <= state.roster.as_of
            )
            for week_start in _completed_week_starts(
                service.start, service.end, state.roster.as_of
            ):
                clipped_start = max(service.start, week_start)
                clipped_end = min(service.end, week_start + timedelta(days=6))
                expected_dates = _eligible_dates(clipped_start, clipped_end, state.roster)
                if not expected_dates:
                    continue
                covered_days = {
                    item.day: item.instructional
                    for item in state.roster.calendar_days
                    if item.day in expected_dates
                }
                if any(day not in covered_days for day in expected_dates):
                    findings.append(
                        _input_finding(
                            state,
                            finding_type="service-calendar-coverage-missing",
                            ref=f"{service.id}:{week_start.isoformat()}",
                            detail=(
                                f"The school calendar does not fully cover {service.type} for "
                                f"the week of {week_start.isoformat()}."
                            ),
                        )
                    )
                    continue
                instructional_days = sum(covered_days.values())
                expected = round(service.minutes_per_week * instructional_days / 5, 2)
                if expected == 0:
                    continue
                ordinary = sum(
                    log.minutes
                    for log in service_logs
                    if log.makeup_for_week_start is None
                    and week_start <= log.delivered_on <= week_start + timedelta(days=6)
                )
                makeup = sum(
                    log.minutes for log in service_logs if log.makeup_for_week_start == week_start
                )
                credited = ordinary + makeup
                variance = round(credited - expected, 2)
                if variance != 0:
                    findings.append(
                        _variance_finding(
                            state,
                            service_id=service.id,
                            service_type=service.type,
                            week_start=week_start,
                            mandated=service.minutes_per_week,
                            expected=expected,
                            ordinary=ordinary,
                            makeup=makeup,
                            variance=variance,
                        )
                    )
        return tuple(findings)


def _completed_week_starts(start_on: date, end_on: date, as_of: date) -> tuple[date, ...]:
    if start_on > end_on or start_on >= as_of:
        return ()
    previous_sunday = as_of - timedelta(days=as_of.weekday() + 1)
    accounting_end = end_on if end_on < as_of else previous_sunday
    if accounting_end < start_on:
        return ()
    current = start_on - timedelta(days=start_on.weekday())
    final = accounting_end - timedelta(days=accounting_end.weekday())
    weeks: list[date] = []
    while current <= final:
        weeks.append(current)
        current += timedelta(days=7)
    return tuple(weeks)


def _date_range(start_on: date, end_on: date) -> tuple[date, ...]:
    return tuple(
        start_on + timedelta(days=offset) for offset in range((end_on - start_on).days + 1)
    )


def _eligible_dates(start_on: date, end_on: date, roster: RosterSnapshot) -> tuple[date, ...]:
    dates = _date_range(start_on, end_on)
    semesters = tuple(term for term in roster.terms if term.kind is TermKind.SEMESTER)
    if not semesters:
        return dates
    return tuple(
        day for day in dates if any(term.start_on <= day <= term.end_on for term in semesters)
    )


def _variance_finding(
    state: RuleState,
    *,
    service_id: UUID,
    service_type: str,
    week_start: date,
    mandated: int,
    expected: float,
    ordinary: int,
    makeup: int,
    variance: float,
) -> Finding:
    credited = ordinary + makeup
    deficit = max(0.0, -variance)
    direction = "short" if variance < 0 else "over"
    return Finding(
        id=finding_id(
            state.approved,
            rule_id=ServicesStatementRule.id,
            finding_type="service-minute-variance",
            ref=f"{service_id}:{week_start.isoformat()}",
        ),
        rule_id=ServicesStatementRule.id,
        citation=ServicesStatementRule.citation,
        finding_type="service-minute-variance",
        severity=FindingSeverity.CRITICAL if variance < 0 else FindingSeverity.INFO,
        student_ref=state.approved.record.student_ref,
        iep_record_version_id=state.approved.row_id,
        detected_on=state.roster.as_of,
        title=f"{service_type} is {abs(variance):g} minutes {direction}",
        detail=(
            f"For the week of {week_start.isoformat()}, {service_type} required {expected:g} "
            f"adjusted minutes and has {credited:g} credited minutes."
        ),
        related_refs={"service_id": str(service_id), "week_start": week_start.isoformat()},
        measurements={
            "mandated_minutes_per_week": mandated,
            "adjusted_expected_minutes": expected,
            "delivered_minutes": ordinary,
            "makeup_minutes": makeup,
            "credited_minutes": credited,
            "variance_minutes": variance,
            "remaining_minutes": deficit,
        },
    )


def _input_finding(state: RuleState, *, finding_type: str, ref: str, detail: str) -> Finding:
    return Finding(
        id=finding_id(
            state.approved,
            rule_id=ServicesStatementRule.id,
            finding_type=finding_type,
            ref=ref,
        ),
        rule_id=ServicesStatementRule.id,
        citation=ServicesStatementRule.citation,
        finding_type=finding_type,
        severity=FindingSeverity.WARNING,
        student_ref=state.approved.record.student_ref,
        iep_record_version_id=state.approved.row_id,
        detected_on=state.roster.as_of,
        title="Service accounting input requires review",
        detail=detail,
        related_refs={"source_ref": ref},
        measurements={},
    )
