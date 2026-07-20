"""Unit tests for deadline rules and school-local calendar behavior."""

from datetime import date, timedelta

import pytest

from bridgeline.rules.calendar import (
    CadenceKind,
    UnsupportedCadenceError,
    parse_progress_cadence,
    previous_instructional_day,
)
from bridgeline.rules.families.deadlines import (
    AnnualReviewRule,
    InitialIEPMeetingRule,
    ProgressReportCadenceRule,
    TriennialReevaluationRule,
)
from bridgeline.rules.types import (
    ApprovedRecord,
    CalendarDay,
    ComplianceProfile,
    DeadlineStatus,
    RosterSnapshot,
    RuleState,
)


def _calendar(start: date, end: date, *holidays: date) -> tuple[CalendarDay, ...]:
    days: list[CalendarDay] = []
    current = start
    while current <= end:
        days.append(
            CalendarDay(
                day=current,
                instructional=current.weekday() < 5 and current not in holidays,
            )
        )
        current += timedelta(days=1)
    return tuple(days)


def test_previous_instructional_day_moves_weekend_and_holiday_earlier() -> None:
    holiday = date(2026, 7, 17)
    days = _calendar(date(2026, 7, 13), date(2026, 7, 20), holiday)

    assert previous_instructional_day(date(2026, 7, 19), days) == date(2026, 7, 16)


@pytest.mark.parametrize(
    ("text", "kind", "amount"),
    [
        ("Weekly", CadenceKind.DAYS, 7),
        ("Every two weeks", CadenceKind.DAYS, 14),
        ("every 6 weeks", CadenceKind.DAYS, 42),
        ("Monthly", CadenceKind.MONTHS, 1),
        ("Quarterly", CadenceKind.MONTHS, 3),
        ("Each grading period", CadenceKind.GRADING_PERIOD, 1),
    ],
)
def test_progress_cadence_finite_grammar(text: str, kind: CadenceKind, amount: int) -> None:
    parsed = parse_progress_cadence(text)

    assert (parsed.kind, parsed.amount) == (kind, amount)


def test_progress_cadence_rejects_unapproved_free_text() -> None:
    with pytest.raises(UnsupportedCadenceError):
        parse_progress_cadence("often enough")


def test_initial_meeting_rule_uses_thirty_calendar_days(
    approved_record: ApprovedRecord, roster: RosterSnapshot
) -> None:
    scoped = roster.model_copy(
        update={
            "calendar_days": _calendar(date(2026, 7, 1), date(2026, 9, 15)),
            "compliance_profile": ComplianceProfile(
                initial_eligibility=True,
                eligibility_determined_on=date(2026, 8, 1),
            ),
        }
    )

    deadlines = InitialIEPMeetingRule().derive_deadlines(approved_record, scoped)

    assert len(deadlines) == 1
    assert deadlines[0].legal_due_on == date(2026, 8, 31)
    assert deadlines[0].citation == "34 CFR §300.323(c)(1)"


def test_annual_review_past_date_is_overdue_not_error(
    approved_record: ApprovedRecord, roster: RosterSnapshot
) -> None:
    record = approved_record.record.model_copy(
        update={
            "dates": approved_record.record.dates.model_copy(
                update={"annual_review": date(2026, 7, 1)}
            )
        }
    )
    approved = approved_record.model_copy(update={"record": record})
    scoped = roster.model_copy(
        update={"calendar_days": _calendar(date(2026, 5, 1), date(2026, 7, 20))}
    )

    deadlines = AnnualReviewRule().derive_deadlines(approved, scoped)

    assert deadlines[0].status is DeadlineStatus.OVERDUE


def test_triennial_reevaluation_uses_school_local_deadline_and_warnings(
    approved_record: ApprovedRecord, roster: RosterSnapshot
) -> None:
    legal_due_on = date(2026, 8, 31)
    record = approved_record.record.model_copy(
        update={
            "dates": approved_record.record.dates.model_copy(
                update={"triennial_reeval": legal_due_on}
            )
        }
    )
    approved = approved_record.model_copy(update={"record": record})
    scoped = roster.model_copy(
        update={"calendar_days": _calendar(date(2026, 7, 1), date(2026, 9, 1))}
    )

    deadline = TriennialReevaluationRule().derive_deadlines(approved, scoped)[0]

    assert deadline.legal_due_on == legal_due_on
    assert deadline.action_due_on == legal_due_on
    assert deadline.warning_30_on == date(2026, 7, 31)
    assert deadline.warning_14_on == date(2026, 8, 17)
    assert deadline.warning_3_on == date(2026, 8, 28)
    assert deadline.citation == "34 CFR §300.303(b)(2)"


def test_missing_triennial_deadline_becomes_typed_review_finding(
    approved_record: ApprovedRecord, roster: RosterSnapshot
) -> None:
    record = approved_record.record.model_copy(
        update={"dates": approved_record.record.dates.model_copy(update={"triennial_reeval": None})}
    )
    approved = approved_record.model_copy(update={"record": record})

    finding = TriennialReevaluationRule().check(RuleState(approved=approved, roster=roster))[0]

    assert finding.finding_type == "triennial-reevaluation-date-missing"
    assert finding.citation == "34 CFR §300.303(b)(2)"


def test_progress_report_rule_derives_each_goal_deadline(
    approved_record: ApprovedRecord, roster: RosterSnapshot
) -> None:
    record = approved_record.record.model_copy(
        update={
            "dates": approved_record.record.dates.model_copy(
                update={"last_progress_report": date(2026, 10, 1)}
            )
        }
    )
    approved = approved_record.model_copy(update={"record": record})
    scoped = roster.model_copy(
        update={"calendar_days": _calendar(date(2026, 9, 1), date(2026, 11, 1))}
    )

    deadlines = ProgressReportCadenceRule().derive_deadlines(approved, scoped)

    assert len(deadlines) == len(record.goals)
    assert deadlines[0].legal_due_on == date(2026, 10, 15)
    assert deadlines[0].citation == "34 CFR §300.320(a)(3)"


def test_unsupported_progress_cadence_becomes_typed_finding(
    approved_record: ApprovedRecord, roster: RosterSnapshot
) -> None:
    goal = approved_record.record.goals[0].model_copy(
        update={"progress_cadence": "whenever appropriate"}
    )
    record = approved_record.record.model_copy(
        update={
            "goals": [goal],
            "dates": approved_record.record.dates.model_copy(
                update={"last_progress_report": date(2026, 10, 1)}
            ),
        }
    )
    approved = approved_record.model_copy(update={"record": record})
    state = RuleState(approved=approved, roster=roster)

    findings = ProgressReportCadenceRule().check(state)

    assert findings[0].finding_type == "progress-cadence-unsupported"
    assert findings[0].citation == "34 CFR §300.320(a)(3)"
