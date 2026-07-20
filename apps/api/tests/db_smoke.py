"""Executable clean-database migration, seed, query, and immutability smoke test."""

import asyncio
import json
from datetime import UTC, date, datetime
from uuid import UUID

from pydantic import JsonValue
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import DBAPIError

from bridgeline.db.iep_records import get_current_approved_record
from bridgeline.db.models import (
    AuditEvent,
    Brief,
    Class,
    Enrollment,
    IEPRecord,
    Obligation,
    PipelineRun,
    Student,
    Teacher,
)
from bridgeline.db.session import async_session_factory

STUDENT_ID = UUID("10000000-0000-4000-8000-000000000001")
TEACHER_ID = UUID("20000000-0000-4000-8000-000000000001")
CLASS_ID = UUID("30000000-0000-4000-8000-000000000001")
ENROLLMENT_ID = UUID("40000000-0000-4000-8000-000000000001")
IEP_LINEAGE_ID = UUID("50000000-0000-4000-8000-000000000001")
APPROVED_VERSION_ID = UUID("50000000-0000-4000-8000-000000000011")
DRAFT_VERSION_ID = UUID("50000000-0000-4000-8000-000000000012")
APPROVED_RUN_ID = UUID("60000000-0000-4000-8000-000000000001")
DRAFT_RUN_ID = UUID("60000000-0000-4000-8000-000000000002")
OBLIGATION_ID = UUID("70000000-0000-4000-8000-000000000001")
ACCOMMODATION_ID = UUID("70000000-0000-4000-8000-000000000002")
BRIEF_ID = UUID("80000000-0000-4000-8000-000000000001")
AUDIT_EVENT_ID = UUID("90000000-0000-4000-8000-000000000001")
NOW = datetime(2026, 7, 19, 4, 0, tzinfo=UTC)


def json_payload(value: dict[str, JsonValue]) -> dict[str, JsonValue]:
    """Preserve a statically typed JSON object for JSONB assignment."""

    return value


async def seed() -> None:
    """Insert every required table and an additional review draft for lineage verification."""

    approved_payload = json_payload(
        {
            "iep_record_id": str(IEP_LINEAGE_ID),
            "student_ref": "student-rivera",
            "version": 1,
            "approval_state": "approved",
        }
    )
    draft_payload = json_payload(
        {
            "iep_record_id": str(IEP_LINEAGE_ID),
            "student_ref": "student-rivera",
            "version": 2,
            "approval_state": "draft",
        }
    )
    brief_payload = json_payload(
        {
            "brief_id": str(BRIEF_ID),
            "teacher_ref": "teacher-nguyen",
            "class_ref": "class-ela-03",
            "status": "draft",
        }
    )
    audit_payload = json_payload(
        {
            "event_id": str(AUDIT_EVENT_ID),
            "event_type": "iep.approved",
            "summary": "Case manager approved IEP version 1.",
        }
    )

    rows = [
        Student(
            id=STUDENT_ID,
            student_ref="student-rivera",
            display_name="Maya Rivera",
        ),
        Teacher(
            id=TEACHER_ID,
            teacher_ref="teacher-nguyen",
            display_name="Alex Nguyen",
            email="alex.nguyen@example.test",
        ),
        Class(
            id=CLASS_ID,
            class_ref="class-ela-03",
            teacher_id=TEACHER_ID,
            name="English Language Arts — Period 3",
            subject="English language arts",
            school_year="2026-2027",
        ),
        Enrollment(
            id=ENROLLMENT_ID,
            student_id=STUDENT_ID,
            class_id=CLASS_ID,
            school_year="2026-2027",
            active=True,
        ),
        PipelineRun(
            id=APPROVED_RUN_ID,
            state="done",
            current_stage="deliver",
            detail="Approved IEP version delivered.",
            started_at=NOW,
            completed_at=NOW,
        ),
        PipelineRun(
            id=DRAFT_RUN_ID,
            state="needs_review",
            current_stage="confidence_gate",
            detail="Re-extracted IEP version is waiting for human review.",
            started_at=NOW,
            completed_at=None,
        ),
        IEPRecord(
            id=APPROVED_VERSION_ID,
            iep_record_id=IEP_LINEAGE_ID,
            version=1,
            student_id=STUDENT_ID,
            pipeline_run_id=APPROVED_RUN_ID,
            extraction_run_id=UUID("50000000-0000-4000-8000-000000000021"),
            approval_state="approved",
            is_current_approved=True,
            payload=approved_payload,
            disability_category="Specific learning disability",
            school_year="2026-2027",
            annual_review=date(2027, 5, 10),
            triennial_reeval=date(2029, 4, 22),
            last_progress_report=None,
            extracted_at=NOW,
            approved_at=NOW,
            superseded_at=None,
        ),
        IEPRecord(
            id=DRAFT_VERSION_ID,
            iep_record_id=IEP_LINEAGE_ID,
            version=2,
            student_id=STUDENT_ID,
            pipeline_run_id=DRAFT_RUN_ID,
            extraction_run_id=UUID("50000000-0000-4000-8000-000000000022"),
            approval_state="draft",
            is_current_approved=False,
            payload=draft_payload,
            disability_category="Specific learning disability",
            school_year="2026-2027",
            annual_review=date(2027, 5, 10),
            triennial_reeval=date(2029, 4, 22),
            last_progress_report=None,
            extracted_at=NOW,
            approved_at=None,
            superseded_at=None,
        ),
        Obligation(
            id=OBLIGATION_ID,
            iep_record_version_id=APPROVED_VERSION_ID,
            student_id=STUDENT_ID,
            assignee_kind="teacher",
            assignee_ref="teacher-nguyen",
            assignee_role="teacher-of-record",
            context_kind="class",
            context_ref="class-ela-03",
            subject="English language arts",
            source_kind="accommodation",
            source_ref=ACCOMMODATION_ID,
            rule_id="teacher-informed-accommodations",
            citation="34 CFR §300.323(d)(2)(ii)",
            action_text="Provide 50 percent extended time on classroom assessments.",
            practice_text=None,
            status="pending",
            confirmed_at=None,
            flag_reason=None,
        ),
        Brief(
            id=BRIEF_ID,
            iep_record_version_id=APPROVED_VERSION_ID,
            teacher_id=TEACHER_ID,
            class_id=CLASS_ID,
            rules_version="2026.07.1",
            status="draft",
            payload=brief_payload,
            generated_at=NOW,
            released_at=None,
            confirmed_at=None,
            flag_reason=None,
        ),
        AuditEvent(
            id=AUDIT_EVENT_ID,
            event_type="iep.approved",
            occurred_at=NOW,
            actor_ref="case-manager-patel",
            actor_role="case_manager",
            subject_type="iep_record",
            subject_ref=str(APPROVED_VERSION_ID),
            payload=audit_payload,
            correlation_id=None,
            pipeline_run_id=APPROVED_RUN_ID,
        ),
    ]

    async with async_session_factory() as session:
        session.add_all([rows[0], rows[1], rows[4], rows[5]])
        await session.flush()
        session.add(rows[2])
        await session.flush()
        session.add_all([rows[3], rows[6], rows[7]])
        await session.flush()
        session.add_all(rows[8:])
        await session.commit()


async def verify_queries() -> None:
    """Query every table and prove a newer draft does not hide the approved version."""

    async with async_session_factory() as session:
        counts = {
            "students": await session.scalar(select(func.count()).select_from(Student)),
            "teachers": await session.scalar(select(func.count()).select_from(Teacher)),
            "classes": await session.scalar(select(func.count()).select_from(Class)),
            "enrollments": await session.scalar(select(func.count()).select_from(Enrollment)),
            "iep_records": await session.scalar(select(func.count()).select_from(IEPRecord)),
            "obligations": await session.scalar(select(func.count()).select_from(Obligation)),
            "briefs": await session.scalar(select(func.count()).select_from(Brief)),
            "audit_events": await session.scalar(select(func.count()).select_from(AuditEvent)),
            "pipeline_runs": await session.scalar(select(func.count()).select_from(PipelineRun)),
        }
        approved = await get_current_approved_record(session, IEP_LINEAGE_ID)
        if approved is None:
            raise AssertionError("current approved IEP version was not found")
        drafts = (
            await session.execute(
                select(IEPRecord).where(
                    IEPRecord.iep_record_id == IEP_LINEAGE_ID,
                    IEPRecord.approval_state == "draft",
                )
            )
        ).scalars()
        draft_versions = sorted(record.version for record in drafts)

    print("ROW_COUNTS=" + json.dumps(counts, sort_keys=True))
    print(
        "CURRENT_APPROVED="
        + json.dumps(
            {
                "iep_record_id": str(approved.iep_record_id),
                "row_id": str(approved.id),
                "version": approved.version,
                "approval_state": approved.approval_state,
                "is_current_approved": approved.is_current_approved,
            },
            sort_keys=True,
        )
    )
    print("REVIEW_DRAFTS=" + json.dumps({"versions": draft_versions}, sort_keys=True))


async def verify_audit_append_only() -> None:
    """Prove the database trigger blocks update and delete operations."""

    async with async_session_factory() as session:
        try:
            await session.execute(
                update(AuditEvent)
                .where(AuditEvent.id == AUDIT_EVENT_ID)
                .values(event_type="iep.modified")
            )
            await session.commit()
        except DBAPIError:
            await session.rollback()
            print("AUDIT_UPDATE=BLOCKED")
        else:
            raise AssertionError("audit event update unexpectedly succeeded")

    async with async_session_factory() as session:
        try:
            await session.execute(delete(AuditEvent).where(AuditEvent.id == AUDIT_EVENT_ID))
            await session.commit()
        except DBAPIError:
            await session.rollback()
            print("AUDIT_DELETE=BLOCKED")
        else:
            raise AssertionError("audit event delete unexpectedly succeeded")

    async with async_session_factory() as session:
        remaining = await session.scalar(select(func.count()).select_from(AuditEvent))
    print("AUDIT_ROWS_AFTER_BLOCKED_MUTATIONS=" + str(remaining))


async def main() -> None:
    """Run the complete Slice 3 database smoke verification."""

    await seed()
    await verify_queries()
    await verify_audit_append_only()


if __name__ == "__main__":
    asyncio.run(main())
