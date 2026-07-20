"""Frozen rule input fixtures."""

from datetime import UTC, date, datetime
from uuid import UUID

import pytest

from bridgeline.rules.types import (
    ApprovedRecord,
    ProviderAssignment,
    RosterClass,
    RosterSnapshot,
    TeacherAssignment,
)
from tests.ingest.conftest import sample_record


@pytest.fixture
def approved_record() -> ApprovedRecord:
    return ApprovedRecord(
        row_id=UUID("eeeeeeee-eeee-4eee-8eee-eeeeeeeeeee1"),
        student_id=UUID("eeeeeeee-eeee-4eee-8eee-eeeeeeeeeee2"),
        record=sample_record(),
    )


@pytest.fixture
def roster(approved_record: ApprovedRecord) -> RosterSnapshot:
    service_id = approved_record.record.services[0].id
    return RosterSnapshot(
        classes=(
            RosterClass(
                class_ref="class-ela",
                subject="English language arts",
                teachers=(TeacherAssignment(teacher_ref="teacher-ela"),),
            ),
            RosterClass(
                class_ref="class-math",
                subject="Mathematics",
                teachers=(
                    TeacherAssignment(teacher_ref="teacher-math"),
                    TeacherAssignment(teacher_ref="teacher-math-co"),
                ),
            ),
        ),
        providers=(
            ProviderAssignment(
                service_id=service_id,
                provider_ref="provider-sped",
                provider_role="Special education teacher",
            ),
        ),
        generated_at=datetime(2026, 7, 20, 3, tzinfo=UTC),
        as_of=date(2026, 7, 20),
    )
