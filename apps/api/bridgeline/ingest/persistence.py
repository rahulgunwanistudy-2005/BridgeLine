"""Persistence boundary for ingest runs and immutable draft IEP versions."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Protocol, cast
from uuid import UUID

from pydantic import JsonValue
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bridgeline.db.models import IEPRecord as IEPRecordRow
from bridgeline.db.models import PipelineRun, Student
from bridgeline.db.schemas import IEPRecord


class IngestStore(Protocol):
    """Typed persistence operations required by the ingest pipeline."""

    async def create_run(self, run_id: UUID) -> None: ...

    async def get_prior_approved(self, lineage_id: UUID) -> IEPRecord | None: ...

    async def save_draft(self, record: IEPRecord, run_id: UUID) -> UUID: ...

    async def set_run_state(self, run_id: UUID, *, state: str, stage: str, detail: str) -> None: ...


class SQLAlchemyIngestStore:
    """Short-transaction Postgres implementation of the ingest persistence boundary."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create_run(self, run_id: UUID) -> None:
        """Persist a queued run before background processing starts."""

        async with self._session_factory.begin() as session:
            session.add(PipelineRun(id=run_id, state="queued", detail="Upload accepted for ingest"))

    async def get_prior_approved(self, lineage_id: UUID) -> IEPRecord | None:
        """Fetch only the current approved version for deterministic reconciliation."""

        async with self._session_factory() as session:
            statement = select(IEPRecordRow.payload).where(
                IEPRecordRow.iep_record_id == lineage_id,
                IEPRecordRow.approval_state == "approved",
                IEPRecordRow.is_current_approved.is_(True),
            )
            payload = (await session.execute(statement)).scalar_one_or_none()
        if payload is None:
            return None
        return IEPRecord.model_validate_json(json.dumps(payload))

    async def save_draft(self, record: IEPRecord, run_id: UUID) -> UUID:
        """Persist the complete IEPRecord, including field confidences, as an immutable draft."""

        async with self._session_factory.begin() as session:
            student = await self._get_or_create_student(session, record.student_ref)
            version_statement = select(func.coalesce(func.max(IEPRecordRow.version), 0)).where(
                IEPRecordRow.iep_record_id == record.iep_record_id
            )
            version = int((await session.execute(version_statement)).scalar_one()) + 1
            payload = serialize_record_payload(record)
            row = IEPRecordRow(
                iep_record_id=record.iep_record_id,
                version=version,
                student_id=student.id,
                pipeline_run_id=run_id,
                extraction_run_id=record.extraction_meta.run_id,
                approval_state="draft",
                is_current_approved=False,
                payload=payload,
                disability_category=record.disability_category,
                school_year=record.school_year,
                annual_review=record.dates.annual_review,
                triennial_reeval=record.dates.triennial_reeval,
                last_progress_report=record.dates.last_progress_report,
                extracted_at=record.extraction_meta.extracted_at,
            )
            session.add(row)
            await session.flush()
            return row.id

    async def set_run_state(self, run_id: UUID, *, state: str, stage: str, detail: str) -> None:
        """Update the resumable run summary while events remain append-only elsewhere."""

        async with self._session_factory.begin() as session:
            run = await session.get(PipelineRun, run_id)
            if run is None:
                raise LookupError(f"pipeline run {run_id} does not exist")
            run.state = state  # type: ignore[assignment]
            run.current_stage = stage
            run.detail = detail
            now = datetime.now(UTC)
            if state == "running" and run.started_at is None:
                run.started_at = now
            if state in {"done", "error"}:
                run.completed_at = now

    @staticmethod
    async def _get_or_create_student(session: AsyncSession, student_ref: str) -> Student:
        result = await session.execute(select(Student).where(Student.student_ref == student_ref))
        student = result.scalar_one_or_none()
        if student is None:
            student = Student(student_ref=student_ref, display_name=student_ref)
            session.add(student)
            await session.flush()
        return student


def serialize_record_payload(record: IEPRecord) -> dict[str, JsonValue]:
    """Serialize the complete canonical record for both draft and approved JSONB payloads."""

    return cast(dict[str, JsonValue], record.model_dump(mode="json"))
