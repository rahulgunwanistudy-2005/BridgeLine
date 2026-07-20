"""Idempotent development seed for rules-engine curl verification."""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime, timedelta
from typing import cast
from uuid import UUID, uuid5

from pydantic import JsonValue
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bridgeline.config import get_settings
from bridgeline.db.models import (
    Class,
    ClassStaff,
    Enrollment,
    PipelineRun,
    Provider,
    SchoolCalendarDay,
    SchoolTerm,
    ServiceAssignment,
    ServiceDeliveryLog,
    Student,
    StudentComplianceProfile,
    Teacher,
)
from bridgeline.db.models import (
    IEPRecord as IEPRecordRow,
)
from bridgeline.db.schemas import (
    Accommodation,
    AccommodationScope,
    AccommodationScopeReference,
    ExtractionMeta,
    FieldConfidences,
    Goal,
    IEPDates,
    IEPRecord,
    Service,
)
from bridgeline.db.session import async_session_factory

STAMP = datetime(2026, 7, 20, 3, tzinfo=UTC)
LINEAGES = tuple(UUID(f"10000000-0000-4000-8000-00000000000{index}") for index in range(1, 4))


async def seed() -> None:
    """Insert stable approved records and assignment facts without deleting user data."""

    if get_settings().app_env == "production":
        raise RuntimeError("rules demo seed is disabled in production")
    async with async_session_factory.begin() as session:
        teachers = await _seed_teachers(session)
        students = await _seed_students(session)
        classes = await _seed_classes(session, teachers)
        records = await _seed_records(session, students)
        await _seed_rosters(session, students, classes, teachers)
        await _seed_provider(session, records[0])
        await _seed_service_logs(session, records[0])
        await _seed_calendar(session)
        await _seed_profiles(session, students)
    print("Seeded three hand-authored current approved IEP records:")
    for lineage in LINEAGES:
        print(f"curl -X POST http://localhost:8000/ieps/{lineage}/obligations/derive")
        print(f"curl http://localhost:8000/ieps/{lineage}/obligations")
    print("curl http://localhost:8000/rules")
    print("curl http://localhost:8000/compliance/deadlines")


async def _seed_teachers(session: AsyncSession) -> dict[str, Teacher]:
    specs = (
        ("teacher-ela", "Anaïs Rivera", "anais@example.test"),
        ("teacher-math", "李 Wei", "wei@example.test"),
        ("teacher-math-co", "Marta Núñez", "marta@example.test"),
        ("teacher-science", "Omar Haddad", "omar@example.test"),
    )
    result: dict[str, Teacher] = {}
    for index, (ref, name, email) in enumerate(specs, start=1):
        row = await session.get(Teacher, UUID(f"20000000-0000-4000-8000-00000000000{index}"))
        if row is None:
            row = Teacher(
                id=UUID(f"20000000-0000-4000-8000-00000000000{index}"),
                teacher_ref=ref,
                display_name=name,
                email=email,
            )
            session.add(row)
        result[ref] = row
    await session.flush()
    return result


async def _seed_students(session: AsyncSession) -> tuple[Student, ...]:
    specs = (
        ("RIV-201", "Zoë García"),
        ("RIV-202", "अर्जुन Patel"),
        ("RIV-203", "Maya O'Connor"),
    )
    rows: list[Student] = []
    for index, (ref, name) in enumerate(specs, start=1):
        row = await session.get(Student, UUID(f"30000000-0000-4000-8000-00000000000{index}"))
        if row is None:
            row = Student(
                id=UUID(f"30000000-0000-4000-8000-00000000000{index}"),
                student_ref=ref,
                display_name=name,
            )
            session.add(row)
        rows.append(row)
    await session.flush()
    return tuple(rows)


async def _seed_classes(session: AsyncSession, teachers: dict[str, Teacher]) -> dict[str, Class]:
    specs = (
        ("class-ela", "English 7", "English language arts", "teacher-ela"),
        ("class-math", "Mathematics 7", "Mathematics", "teacher-math"),
        ("class-science", "Science 7", "Science", "teacher-science"),
    )
    result: dict[str, Class] = {}
    for index, (ref, name, subject, teacher_ref) in enumerate(specs, start=1):
        row = await session.get(Class, UUID(f"40000000-0000-4000-8000-00000000000{index}"))
        if row is None:
            row = Class(
                id=UUID(f"40000000-0000-4000-8000-00000000000{index}"),
                class_ref=ref,
                teacher_id=teachers[teacher_ref].id,
                name=name,
                subject=subject,
                school_year="2026-2027",
            )
            session.add(row)
        result[ref] = row
    await session.flush()
    return result


async def _seed_records(
    session: AsyncSession, students: tuple[Student, ...]
) -> tuple[IEPRecordRow, ...]:
    rows: list[IEPRecordRow] = []
    for index, (lineage, student) in enumerate(zip(LINEAGES, students, strict=True), start=1):
        row_id = UUID(f"50000000-0000-4000-8000-00000000000{index}")
        row = await session.get(IEPRecordRow, row_id)
        if row is None:
            run_id = UUID(f"60000000-0000-4000-8000-00000000000{index}")
            session.add(PipelineRun(id=run_id, state="done", detail="Hand-authored rules seed"))
            record = _record(index, lineage, student.student_ref)
            row = IEPRecordRow(
                id=row_id,
                iep_record_id=lineage,
                version=1,
                student_id=student.id,
                pipeline_run_id=run_id,
                extraction_run_id=record.extraction_meta.run_id,
                approval_state="approved",
                is_current_approved=True,
                payload=cast(dict[str, JsonValue], record.model_dump(mode="json")),
                disability_category=record.disability_category,
                school_year=record.school_year,
                annual_review=record.dates.annual_review,
                triennial_reeval=record.dates.triennial_reeval,
                last_progress_report=record.dates.last_progress_report,
                extracted_at=STAMP,
                approved_at=STAMP,
            )
            session.add(row)
        rows.append(row)
    await session.flush()
    return tuple(rows)


async def _seed_rosters(
    session: AsyncSession,
    students: tuple[Student, ...],
    classes: dict[str, Class],
    teachers: dict[str, Teacher],
) -> None:
    for student_index, student in enumerate(students, start=1):
        for class_index, classroom in enumerate(classes.values(), start=1):
            enrollment_id = UUID(f"70000000-0000-4000-8000-0000000000{student_index}{class_index}")
            if await session.get(Enrollment, enrollment_id) is None:
                session.add(
                    Enrollment(
                        id=enrollment_id,
                        student_id=student.id,
                        class_id=classroom.id,
                        school_year="2026-2027",
                        active=True,
                    )
                )
    assignments = (
        (1, classes["class-ela"], teachers["teacher-ela"]),
        (2, classes["class-math"], teachers["teacher-math"]),
        (3, classes["class-math"], teachers["teacher-math-co"]),
        (4, classes["class-science"], teachers["teacher-science"]),
    )
    for index, classroom, teacher in assignments:
        assignment_id = UUID(f"80000000-0000-4000-8000-00000000000{index}")
        if await session.get(ClassStaff, assignment_id) is None:
            session.add(
                ClassStaff(
                    id=assignment_id,
                    class_id=classroom.id,
                    teacher_id=teacher.id,
                    role="teacher-of-record",
                    active=True,
                )
            )


async def _seed_provider(session: AsyncSession, record: IEPRecordRow) -> None:
    provider_id = UUID("90000000-0000-4000-8000-000000000001")
    if await session.get(Provider, provider_id) is None:
        session.add(
            Provider(
                id=provider_id,
                provider_ref="provider-slp",
                display_name="Renée Dubois",
                role="Speech-language pathologist",
            )
        )
    assignment_id = UUID("90000000-0000-4000-8000-000000000002")
    if await session.get(ServiceAssignment, assignment_id) is None:
        service_id = _record(1, LINEAGES[0], "RIV-201").services[0].id
        session.add(
            ServiceAssignment(
                id=assignment_id,
                iep_record_version_id=record.id,
                service_id=service_id,
                provider_id=provider_id,
                active=True,
            )
        )


async def _seed_service_logs(session: AsyncSession, record: IEPRecordRow) -> None:
    service_id = _record(1, LINEAGES[0], "RIV-201").services[0].id
    specs = (
        (
            UUID("91000000-0000-4000-8000-000000000001"),
            date(2026, 10, 6),
            30,
            "provider-slp",
            None,
            None,
        ),
        (
            UUID("91000000-0000-4000-8000-000000000002"),
            date(2026, 10, 8),
            20,
            "provider-slp-substitute",
            "provider-slp",
            None,
        ),
        (
            UUID("91000000-0000-4000-8000-000000000003"),
            date(2026, 10, 20),
            10,
            "provider-slp",
            None,
            date(2026, 10, 5),
        ),
    )
    for log_id, delivered_on, minutes, provider_ref, substitute_for_ref, target_week in specs:
        if await session.get(ServiceDeliveryLog, log_id) is None:
            session.add(
                ServiceDeliveryLog(
                    id=log_id,
                    iep_record_version_id=record.id,
                    service_id=service_id,
                    delivered_on=delivered_on,
                    minutes=minutes,
                    provider_ref=provider_ref,
                    substitute_for_ref=substitute_for_ref,
                    makeup_for_week_start=target_week,
                )
            )


async def _seed_calendar(session: AsyncSession) -> None:
    existing = set(
        (
            await session.scalars(
                select(SchoolCalendarDay.day).where(SchoolCalendarDay.school_year == "2026-2027")
            )
        ).all()
    )
    holidays = {date(2026, 11, 26), date(2026, 12, 25), date(2027, 1, 1)}
    current = date(2026, 6, 1)
    end = date(2027, 7, 31)
    namespace = UUID("e0000000-0000-4000-8000-000000000001")
    while current <= end:
        if current not in existing:
            in_instructional_year = date(2026, 8, 17) <= current <= date(2027, 5, 28)
            session.add(
                SchoolCalendarDay(
                    id=uuid5(namespace, current.isoformat()),
                    school_year="2026-2027",
                    day=current,
                    instructional=(
                        in_instructional_year and current.weekday() < 5 and current not in holidays
                    ),
                )
            )
        current += timedelta(days=1)
    terms = (
        ("2026-2027-semester-1", "semester", date(2026, 8, 17), date(2026, 12, 18)),
        ("2026-2027-semester-2", "semester", date(2027, 1, 4), date(2027, 5, 28)),
        ("2026-2027-gp-1", "grading_period", date(2026, 8, 17), date(2026, 10, 16)),
        ("2026-2027-gp-2", "grading_period", date(2026, 10, 19), date(2026, 12, 18)),
        ("2026-2027-gp-3", "grading_period", date(2027, 1, 4), date(2027, 3, 12)),
        ("2026-2027-gp-4", "grading_period", date(2027, 3, 15), date(2027, 5, 28)),
    )
    for index, (term_ref, kind, start_on, end_on) in enumerate(terms, start=1):
        term_id = UUID(f"e1000000-0000-4000-8000-00000000000{index}")
        if await session.get(SchoolTerm, term_id) is None:
            session.add(
                SchoolTerm(
                    id=term_id,
                    term_ref=term_ref,
                    school_year="2026-2027",
                    kind=kind,
                    start_on=start_on,
                    end_on=end_on,
                )
            )


async def _seed_profiles(session: AsyncSession, students: tuple[Student, ...]) -> None:
    for index, student in enumerate(students, start=1):
        profile_id = UUID(f"e2000000-0000-4000-8000-00000000000{index}")
        if await session.get(StudentComplianceProfile, profile_id) is None:
            session.add(
                StudentComplianceProfile(
                    id=profile_id,
                    student_id=student.id,
                    school_year="2026-2027",
                    initial_eligibility=False,
                    eligibility_determined_on=None,
                )
            )


def _record(index: int, lineage: UUID, student_ref: str) -> IEPRecord:
    all_text = (
        "Provide 50 percent extended time on classroom assessments."
        if index < 3
        else "Provide visual directions, a quiet testing location, and repetition of directions "
        + "when requested, while preserving the exact instructional objective. " * 8
    )
    accommodation_id = UUID(f"a0000000-0000-4000-8000-0000000000{index}1")
    accommodations = [
        Accommodation(
            id=accommodation_id,
            text=all_text,
            applies_to_refs=[
                AccommodationScopeReference(
                    scope=AccommodationScope.ALL,
                    ref="across all classes",
                    source_page=2,
                    source_quote="across all classes",
                    confidence=1.0,
                )
            ],
            source_page=2,
            source_quote=all_text[:80],
            confidence=1.0,
            reconciliation_status=None,
        ),
        Accommodation(
            id=UUID(f"a0000000-0000-4000-8000-0000000000{index}2"),
            text=(
                "Use a four-function calculator."
                if index != 2
                else "Provide 50 percent extended time on classroom assessments."
            ),
            applies_to_refs=[
                AccommodationScopeReference(
                    scope=AccommodationScope.SUBJECT,
                    ref="Mathematics",
                    source_page=3,
                    source_quote="in mathematics",
                    confidence=1.0,
                )
            ],
            source_page=3,
            source_quote="calculator or extended time in mathematics",
            confidence=1.0,
            reconciliation_status=None,
        ),
    ]
    return IEPRecord(
        iep_record_id=lineage,
        student_ref=student_ref,
        disability_category="Specific learning disability",
        school_year="2026-2027",
        accommodations=accommodations,
        services=[
            Service(
                id=UUID(f"b0000000-0000-4000-8000-0000000000{index}1"),
                type="Speech-language service",
                minutes_per_week=60,
                frequency="30 minutes, twice weekly",
                provider_role="Speech-language pathologist",
                start=date(2026, 8, 17),
                end=date(2027, 5, 28),
                source_page=4,
                source_quote="Speech-language service, 30 minutes twice weekly",
                confidence=1.0,
                reconciliation_status=None,
            )
        ],
        goals=[
            Goal(
                id=UUID(f"c0000000-0000-4000-8000-0000000000{index}1"),
                text="Identify the main idea with 80 percent accuracy.",
                baseline="45 percent accuracy.",
                target="80 percent across three probes.",
                measure="Curriculum-based reading probe",
                progress_cadence="Every two weeks",
                source_page=5,
                source_quote="identify the main idea with 80 percent accuracy",
                confidence=1.0,
                reconciliation_status=None,
            )
        ],
        dates=IEPDates(
            annual_review=date(2027, 5, 10),
            triennial_reeval=date(2029, 4, 22),
            last_progress_report=date(2026, 10, 1),
        ),
        field_confidences=FieldConfidences(
            student_ref=1.0,
            disability_category=1.0,
            school_year=1.0,
            annual_review=1.0,
            triennial_reeval=1.0,
            last_progress_report=1.0,
        ),
        extraction_meta=ExtractionMeta(
            model="hand-authored-approved",
            run_id=UUID(f"d0000000-0000-4000-8000-0000000000{index}1"),
            page_count=5,
            legibility_scores=[1.0] * 5,
            extracted_at=STAMP,
        ),
    )


if __name__ == "__main__":
    asyncio.run(seed())
