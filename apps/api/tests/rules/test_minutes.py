"""Unit tests for school-calendar service-minute accounting."""

from datetime import date, timedelta
from uuid import UUID

from bridgeline.rules.families.minutes import ServicesStatementRule
from bridgeline.rules.types import (
    ApprovedRecord,
    CalendarDay,
    RosterSnapshot,
    RuleState,
    SchoolTerm,
    ServiceDeliveryLog,
    TermKind,
)


def _calendar(start: date, end: date, *holidays: date) -> tuple[CalendarDay, ...]:
    return tuple(
        CalendarDay(
            day=start + timedelta(days=offset),
            instructional=(start + timedelta(days=offset)).weekday() < 5
            and start + timedelta(days=offset) not in holidays,
        )
        for offset in range((end - start).days + 1)
    )


def _log(
    approved: ApprovedRecord,
    *,
    log_id: int,
    delivered_on: date,
    minutes: int,
    substitute_for_ref: str | None = None,
    makeup_for_week_start: date | None = None,
) -> ServiceDeliveryLog:
    return ServiceDeliveryLog(
        log_id=UUID(f"f0000000-0000-4000-8000-{log_id:012d}"),
        service_id=approved.record.services[0].id,
        delivered_on=delivered_on,
        minutes=minutes,
        provider_ref="provider-slp-sub" if substitute_for_ref else "provider-slp",
        substitute_for_ref=substitute_for_ref,
        makeup_for_week_start=makeup_for_week_start,
    )


def _state(
    approved: ApprovedRecord,
    roster: RosterSnapshot,
    *,
    start_on: date,
    end_on: date,
    as_of: date,
    holidays: tuple[date, ...] = (),
    logs: tuple[ServiceDeliveryLog, ...] = (),
    terms: tuple[SchoolTerm, ...] = (),
) -> RuleState:
    service = approved.record.services[0].model_copy(update={"start": start_on, "end": end_on})
    record = approved.record.model_copy(update={"services": [service]})
    scoped_approved = approved.model_copy(update={"record": record})
    scoped_roster = roster.model_copy(
        update={
            "calendar_days": _calendar(start_on, end_on, *holidays),
            "service_logs": logs,
            "terms": terms,
            "as_of": as_of,
        }
    )
    return RuleState(approved=scoped_approved, roster=scoped_roster)


def test_full_week_deficit_reports_required_delivered_and_remaining(
    approved_record: ApprovedRecord, roster: RosterSnapshot
) -> None:
    start = date(2026, 10, 5)
    state = _state(
        approved_record,
        roster,
        start_on=start,
        end_on=date(2026, 10, 9),
        as_of=date(2026, 10, 12),
        logs=(_log(approved_record, log_id=1, delivered_on=start, minutes=100),),
    )

    finding = ServicesStatementRule().check(state)[0]

    assert finding.citation == "34 CFR §300.320(a)(4)"
    assert finding.measurements["adjusted_expected_minutes"] == 150.0
    assert finding.measurements["delivered_minutes"] == 100
    assert finding.measurements["remaining_minutes"] == 50.0


def test_holiday_and_midweek_start_prorate_against_five_day_week(
    approved_record: ApprovedRecord, roster: RosterSnapshot
) -> None:
    start = date(2026, 10, 7)
    state = _state(
        approved_record,
        roster,
        start_on=start,
        end_on=date(2026, 10, 9),
        as_of=date(2026, 10, 12),
        holidays=(date(2026, 10, 8),),
    )

    finding = ServicesStatementRule().check(state)[0]

    assert finding.measurements["adjusted_expected_minutes"] == 60.0


def test_substitute_delivery_counts_as_ordinary_minutes(
    approved_record: ApprovedRecord, roster: RosterSnapshot
) -> None:
    start = date(2026, 10, 5)
    state = _state(
        approved_record,
        roster,
        start_on=start,
        end_on=date(2026, 10, 9),
        as_of=date(2026, 10, 12),
        logs=(
            _log(
                approved_record,
                log_id=2,
                delivered_on=date(2026, 10, 6),
                minutes=150,
                substitute_for_ref="provider-slp",
            ),
        ),
    )

    assert ServicesStatementRule().check(state) == ()


def test_makeup_minutes_credit_only_the_explicit_target_week(
    approved_record: ApprovedRecord, roster: RosterSnapshot
) -> None:
    start = date(2026, 10, 5)
    state = _state(
        approved_record,
        roster,
        start_on=start,
        end_on=date(2026, 10, 9),
        as_of=date(2026, 10, 21),
        logs=(
            _log(approved_record, log_id=3, delivered_on=start, minutes=100),
            _log(
                approved_record,
                log_id=4,
                delivered_on=date(2026, 10, 20),
                minutes=50,
                makeup_for_week_start=start,
            ),
        ),
    )

    assert ServicesStatementRule().check(state) == ()


def test_semester_boundary_excludes_days_outside_the_term(
    approved_record: ApprovedRecord, roster: RosterSnapshot
) -> None:
    start = date(2026, 12, 14)
    term = SchoolTerm(
        term_ref="semester-1",
        kind=TermKind.SEMESTER,
        start_on=start,
        end_on=date(2026, 12, 16),
    )
    state = _state(
        approved_record,
        roster,
        start_on=start,
        end_on=date(2026, 12, 18),
        as_of=date(2026, 12, 21),
        terms=(term,),
    )

    finding = ServicesStatementRule().check(state)[0]

    assert finding.measurements["adjusted_expected_minutes"] == 90.0


def test_noninstructional_week_emits_no_variance(
    approved_record: ApprovedRecord, roster: RosterSnapshot
) -> None:
    start = date(2026, 12, 21)
    weekdays = tuple(start + timedelta(days=offset) for offset in range(5))
    state = _state(
        approved_record,
        roster,
        start_on=start,
        end_on=date(2026, 12, 25),
        as_of=date(2026, 12, 28),
        holidays=weekdays,
    )

    assert ServicesStatementRule().check(state) == ()
