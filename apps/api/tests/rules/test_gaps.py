"""Unit tests for implementation-gap detection and UX copy."""

from datetime import date, timedelta
from uuid import UUID

from bridgeline.rules.families.distribution import (
    TeacherAccommodationsRule,
    TeacherResponsibilitiesRule,
)
from bridgeline.rules.families.gaps import IEPInEffectRule, ServicesWithoutDelayRule
from bridgeline.rules.types import (
    AccommodationClassState,
    ApprovedRecord,
    BriefSnapshot,
    CalendarDay,
    DistrictRuleState,
    RosterSnapshot,
    RosterStudent,
    RuleState,
    ServiceDelayReason,
)


def _calendar(start: date, end: date) -> tuple[CalendarDay, ...]:
    return tuple(
        CalendarDay(
            day=start + timedelta(days=offset),
            instructional=(start + timedelta(days=offset)).weekday() < 5,
        )
        for offset in range((end - start).days + 1)
    )


def test_released_brief_unconfirmed_after_three_school_days(
    approved_record: ApprovedRecord, roster: RosterSnapshot
) -> None:
    scoped = roster.model_copy(
        update={
            "briefs": (
                BriefSnapshot(
                    brief_id=UUID("f1000000-0000-4000-8000-000000000001"),
                    class_ref="class-math",
                    teacher_ref="teacher-math",
                    status="released",
                    released_on=date(2026, 7, 13),
                ),
            ),
            "calendar_days": _calendar(date(2026, 7, 13), date(2026, 7, 16)),
            "as_of": date(2026, 7, 16),
        }
    )

    findings = TeacherResponsibilitiesRule().check(
        RuleState(approved=approved_record, roster=scoped)
    )

    brief_finding = next(item for item in findings if item.finding_type == "brief-unconfirmed")
    assert brief_finding.measurements["delay_days"] == 3
    assert brief_finding.citation == "34 CFR §300.323(d)(2)(i)"


def test_partial_confirmation_has_exact_three_of_six_message(
    approved_record: ApprovedRecord, roster: RosterSnapshot
) -> None:
    accommodation = approved_record.record.accommodations[0]
    states = tuple(
        AccommodationClassState(
            accommodation_id=accommodation.id,
            class_ref=f"class-{index}",
            obligation_refs=(UUID(f"f2000000-0000-4000-8000-{index:012d}"),),
            confirmed=index <= 3,
        )
        for index in range(1, 7)
    )
    scoped = roster.model_copy(update={"accommodation_classes": states})

    finding = TeacherAccommodationsRule().check(RuleState(approved=approved_record, roster=scoped))[
        0
    ]

    expected = f"{accommodation.text} is confirmed in 3 of 6 classes; 3 classes remain unconfirmed."
    assert finding.title == expected
    assert finding.detail == expected
    assert finding.measurements["confirmed_classes"] == 3
    assert finding.measurements["total_classes"] == 6


def test_service_delay_uses_configured_school_day_policy(
    approved_record: ApprovedRecord, roster: RosterSnapshot
) -> None:
    approved = approved_record.model_copy(update={"approved_on": date(2026, 8, 3)})
    scoped = roster.model_copy(
        update={
            "calendar_days": _calendar(date(2026, 8, 3), date(2026, 8, 17)),
            "service_start_delay_school_days": 5,
        }
    )

    finding = ServicesWithoutDelayRule().check(RuleState(approved=approved, roster=scoped))[0]

    assert finding.measurements["delay_days"] == 9
    assert finding.measurements["operational_policy_school_days"] == 5
    assert "district policy" in finding.detail


def test_documented_reason_suppresses_service_delay(
    approved_record: ApprovedRecord, roster: RosterSnapshot
) -> None:
    service = approved_record.record.services[0]
    approved = approved_record.model_copy(update={"approved_on": date(2026, 8, 3)})
    scoped = roster.model_copy(
        update={
            "calendar_days": _calendar(date(2026, 8, 3), date(2026, 8, 17)),
            "service_start_delay_school_days": 0,
            "service_delay_reasons": (
                ServiceDelayReason(
                    service_id=service.id,
                    reason="Family requested the documented later start.",
                ),
            ),
        }
    )

    assert ServicesWithoutDelayRule().check(RuleState(approved=approved, roster=scoped)) == ()


def test_active_roster_student_without_approved_iep_is_flagged() -> None:
    state = DistrictRuleState(
        students=(
            RosterStudent(student_ref="RIV-404", school_year="2026-2027"),
            RosterStudent(
                student_ref="RIV-200",
                school_year="2026-2027",
                current_approved_iep_version_id=UUID("f3000000-0000-4000-8000-000000000001"),
            ),
        ),
        as_of=date(2026, 8, 17),
    )

    findings = IEPInEffectRule().check_district(state)

    assert len(findings) == 1
    assert findings[0].student_ref == "RIV-404"
    assert findings[0].iep_record_version_id is None
    assert findings[0].citation == "34 CFR §300.323(a)"
