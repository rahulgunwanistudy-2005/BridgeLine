"""Load ground-truth records and build rule-engine inputs from district data."""

from __future__ import annotations

import csv
import json
from datetime import UTC, date, datetime, timedelta
from uuid import NAMESPACE_URL, UUID, uuid5

from bridgeline.db.schemas import IEPRecord
from bridgeline.rules.types import (
    AccommodationClassState,
    ApprovedRecord,
    CalendarDay,
    ComplianceProfile,
    ProviderAssignment,
    RosterClass,
    RosterSnapshot,
    SchoolTerm,
    ServiceDeliveryLog,
    TeacherAssignment,
    TermKind,
)

from harness.config import (
    DISTRICT_DIR,
    GROUND_TRUTH_DIR,
    PROGRESS_DIR,
    REFERENCE_DATE,
)

HARNESS_NAMESPACE = UUID("a3f8c0e2-7b4d-4e5a-9c1f-2d8b6e0f3a7c")
GENERATED_AT = datetime(2026, 11, 13, 12, 0, 0, tzinfo=UTC)

SEMESTER_1_START = date(2026, 8, 17)
SEMESTER_1_END = date(2026, 12, 18)
SEMESTER_2_START = date(2027, 1, 4)
SEMESTER_2_END = date(2027, 5, 28)

GP_TERMS = (
    ("2026-2027-gp-1", TermKind.GRADING_PERIOD, date(2026, 8, 17), date(2026, 10, 16)),
    ("2026-2027-gp-2", TermKind.GRADING_PERIOD, date(2026, 10, 19), date(2026, 12, 18)),
    ("2026-2027-gp-3", TermKind.GRADING_PERIOD, date(2027, 1, 4), date(2027, 3, 12)),
    ("2026-2027-gp-4", TermKind.GRADING_PERIOD, date(2027, 3, 15), date(2027, 5, 28)),
)


def load_canonical_records() -> list[IEPRecord]:
    """Load all 12 canonical IEPRecords from ground truth."""

    records = []
    for path in sorted(GROUND_TRUTH_DIR.glob("*.iep.json")):
        record = IEPRecord.model_validate_json(path.read_text(encoding="utf-8"))
        records.append(record)
    return records


def load_record(student_ref: str) -> IEPRecord:
    """Load one canonical IEPRecord by student reference."""

    path = GROUND_TRUTH_DIR / f"{student_ref}.iep.json"
    return IEPRecord.model_validate_json(path.read_text(encoding="utf-8"))


def load_district_data() -> dict:
    """Load the full district JSON for reference."""

    return json.loads((DISTRICT_DIR / "district.json").read_text(encoding="utf-8"))


def load_classes() -> list[dict]:
    """Load district classes."""

    return json.loads((DISTRICT_DIR / "classes.json").read_text(encoding="utf-8"))


def load_teachers() -> list[dict]:
    """Load district teachers."""

    return json.loads((DISTRICT_DIR / "teachers.json").read_text(encoding="utf-8"))


def load_subjects() -> dict[str, str]:
    """Load subject_ref → name mapping."""

    subjects = json.loads((DISTRICT_DIR / "subjects.json").read_text(encoding="utf-8"))
    return {s["subject_ref"]: s["name"] for s in subjects}


def load_students() -> list[dict]:
    """Load district students."""

    return json.loads((DISTRICT_DIR / "students.json").read_text(encoding="utf-8"))


def load_enrollments() -> list[dict]:
    """Load district enrollments."""

    return json.loads((DISTRICT_DIR / "enrollments.json").read_text(encoding="utf-8"))


def load_calendar() -> dict:
    """Load district calendar."""

    return json.loads((DISTRICT_DIR / "calendar.json").read_text(encoding="utf-8"))


def load_accommodation_confirmations() -> list[dict]:
    """Load accommodation confirmation rows from CSV."""

    path = PROGRESS_DIR / "accommodation_confirmations.csv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def load_service_logs(student_ref: str) -> list[dict]:
    """Load service delivery logs for one student."""

    path = PROGRESS_DIR / "service_logs" / f"{student_ref}.csv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def build_approved_record(record: IEPRecord) -> ApprovedRecord:
    """Build an ApprovedRecord with deterministic IDs from a ground-truth IEPRecord."""

    row_id = uuid5(HARNESS_NAMESPACE, f"approved/{record.student_ref}")
    student_id = uuid5(HARNESS_NAMESPACE, f"student/{record.student_ref}")
    return ApprovedRecord(
        row_id=row_id,
        student_id=student_id,
        record=record,
    )


def build_roster_snapshot(
    record: IEPRecord,
    *,
    include_service_logs: bool = False,
    include_confirmations: bool = False,
) -> RosterSnapshot:
    """Build a RosterSnapshot from district data for one student."""

    classes_data = load_classes()
    subjects = load_subjects()
    enrollments = load_enrollments()

    student_class_refs = {
        e["class_ref"]
        for e in enrollments
        if e["student_ref"] == record.student_ref
    }

    roster_classes: list[RosterClass] = []
    for cls in classes_data:
        if cls["class_ref"] not in student_class_refs:
            continue
        subject_name = subjects.get(cls["subject_ref"], cls["name"])
        teachers = tuple(
            TeacherAssignment(
                teacher_ref=teacher_ref,
                role="teacher-of-record",
            )
            for teacher_ref in cls["teachers_of_record"]
        )
        roster_classes.append(
            RosterClass(
                class_ref=cls["class_ref"],
                subject=subject_name,
                teachers=teachers,
            )
        )

    providers: tuple[ProviderAssignment, ...] = ()

    accommodation_classes: tuple[AccommodationClassState, ...] = ()
    if include_confirmations:
        confirmations = load_accommodation_confirmations()
        student_confirmations = [
            row for row in confirmations
            if row["student_ref"] == record.student_ref
        ]
        acc_states: list[AccommodationClassState] = []
        for row in student_confirmations:
            acc_states.append(
                AccommodationClassState(
                    accommodation_id=UUID(row["accommodation_id"]),
                    class_ref=row["class_ref"],
                    obligation_refs=(uuid5(NAMESPACE_URL, row["row_id"]),),
                    confirmed=row["confirmed"] == "true",
                )
            )
        accommodation_classes = tuple(acc_states)

    service_logs_tuple: tuple[ServiceDeliveryLog, ...] = ()
    if include_service_logs:
        raw_logs = load_service_logs(record.student_ref)
        logs: list[ServiceDeliveryLog] = []
        for row in raw_logs:
            service_type = row["service_type"]
            matching_services = [
                s for s in record.services if s.type == service_type
            ]
            if not matching_services:
                continue
            service = matching_services[0]
            logs.append(
                ServiceDeliveryLog(
                    log_id=uuid5(HARNESS_NAMESPACE, f"log/{row['row_id']}"),
                    service_id=service.id,
                    delivered_on=date.fromisoformat(row["date"]),
                    minutes=int(row["minutes_delivered"]),
                    provider_ref=row["provider_role"],
                )
            )
        service_logs_tuple = tuple(logs)

    calendar_days = _build_calendar_days()
    terms = _build_terms()

    return RosterSnapshot(
        classes=tuple(roster_classes),
        providers=providers,
        accommodation_classes=accommodation_classes,
        service_logs=service_logs_tuple,
        calendar_days=calendar_days,
        terms=terms,
        compliance_profile=ComplianceProfile(),
        generated_at=GENERATED_AT,
        as_of=REFERENCE_DATE,
    )


def _build_calendar_days() -> tuple[CalendarDay, ...]:
    """Build school calendar days from district data."""

    cal = load_calendar()
    holidays = {h["date"] for h in cal["holidays"]}
    first = date.fromisoformat(cal["first_instructional_day"])
    last = date.fromisoformat(cal["last_instructional_day"])

    days: list[CalendarDay] = []
    current = first
    while current <= last:
        instructional = (
            current.weekday() < 5
            and current.isoformat() not in holidays
        )
        days.append(CalendarDay(day=current, instructional=instructional))
        current += timedelta(days=1)
    return tuple(days)


def _build_terms() -> tuple[SchoolTerm, ...]:
    """Build semester and grading period terms."""

    terms = [
        SchoolTerm(
            term_ref="2026-2027-semester-1",
            kind=TermKind.SEMESTER,
            start_on=SEMESTER_1_START,
            end_on=SEMESTER_1_END,
        ),
        SchoolTerm(
            term_ref="2026-2027-semester-2",
            kind=TermKind.SEMESTER,
            start_on=SEMESTER_2_START,
            end_on=SEMESTER_2_END,
        ),
    ]
    for ref, kind, start, end in GP_TERMS:
        terms.append(SchoolTerm(term_ref=ref, kind=kind, start_on=start, end_on=end))
    return tuple(terms)
