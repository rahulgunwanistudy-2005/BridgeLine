"""Shared, schema-valid ingest test records."""

from datetime import UTC, date, datetime
from uuid import UUID

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


def sample_record(*, accommodation_confidence: float = 0.98) -> IEPRecord:
    """Return a compact valid record that tests may safely customize."""

    return IEPRecord(
        iep_record_id=UUID("11111111-1111-4111-8111-111111111111"),
        student_ref="RIV-204",
        disability_category="Specific learning disability",
        school_year="2026-2027",
        accommodations=[
            Accommodation(
                id=UUID("11111111-1111-4111-8111-111111111112"),
                text="Provide 50 percent extended time on classroom assessments.",
                applies_to_refs=[
                    AccommodationScopeReference(
                        scope=AccommodationScope.ALL,
                        ref="across all classes",
                        source_page=2,
                        source_quote="50% extended time across all classes",
                        confidence=accommodation_confidence,
                    )
                ],
                source_page=2,
                source_quote="50% extended time on classroom assessments",
                confidence=accommodation_confidence,
                reconciliation_status=None,
            )
        ],
        services=[
            Service(
                id=UUID("11111111-1111-4111-8111-111111111113"),
                type="Specialized academic instruction",
                minutes_per_week=150,
                frequency="30 minutes, five times weekly",
                provider_role="Special education teacher",
                start=date(2026, 8, 17),
                end=date(2027, 5, 28),
                source_page=2,
                source_quote="Specialized academic instruction | 30 | 5x weekly",
                confidence=0.96,
                reconciliation_status=None,
            )
        ],
        goals=[
            Goal(
                id=UUID("11111111-1111-4111-8111-111111111114"),
                text="Identify the main idea with 80 percent accuracy.",
                baseline="Currently identifies the main idea with 45 percent accuracy.",
                target="80 percent across three consecutive probes.",
                measure="Curriculum-based reading probe",
                progress_cadence="Every two weeks",
                source_page=3,
                source_quote="identify the main idea with 80% accuracy",
                confidence=0.94,
                reconciliation_status=None,
            )
        ],
        dates=IEPDates(
            annual_review=date(2027, 5, 10),
            triennial_reeval=date(2029, 4, 22),
            last_progress_report=None,
        ),
        field_confidences=FieldConfidences(
            student_ref=0.99,
            disability_category=0.97,
            school_year=0.99,
            annual_review=0.98,
            triennial_reeval=0.96,
            last_progress_report=0.0,
        ),
        extraction_meta=ExtractionMeta(
            model="gemini-test",
            run_id=UUID("11111111-1111-4111-8111-111111111115"),
            page_count=3,
            legibility_scores=[0.99, 0.95, 0.91],
            extracted_at=datetime(2026, 7, 19, 3, tzinfo=UTC),
        ),
    )
