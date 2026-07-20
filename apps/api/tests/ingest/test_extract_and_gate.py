"""Tests for source-grounded extraction and fail-closed confidence gating."""

from bridgeline.db.schemas import (
    AccommodationScope,
    AccommodationScopeReference,
    ReconciliationStatus,
)
from bridgeline.ingest.extract import deduplicate_accommodations
from bridgeline.ingest.gate import ConfidenceGate, GateState
from bridgeline.llm.prompts import PromptRegistry

from .conftest import sample_record


def test_extraction_prompt_is_verbatim_first_and_fail_closed() -> None:
    """The versioned prompt explicitly carries the silent-wrong safety contract."""

    prompt = PromptRegistry().load("iep_extract")

    assert "VERBATIM" in prompt
    assert "source_quote" in prompt and "source_page" in prompt
    assert "NEVER invent" in prompt
    assert "null" in prompt and "confidence 0" in prompt
    assert "two-column" in prompt and "service-minute" in prompt
    assert 'scope: "all"' in prompt
    assert "all academic subjects" in prompt
    assert "never `all`" in prompt
    assert "Never default missing or ambiguous" in prompt
    assert "scope to `all`" in prompt


def test_duplicate_accommodation_phrasing_is_not_silently_duplicated() -> None:
    """Formatting-only duplicates collapse while retaining the strongest evidence."""

    original = sample_record().accommodations[0]
    duplicate = original.model_copy(
        update={
            "id": "22222222-2222-4222-8222-222222222222",
            "text": "  PROVIDE 50 percent extended time on classroom assessments.  ",
            "confidence": 0.72,
        }
    )

    result = deduplicate_accommodations([duplicate, original])

    assert result == [original]


def test_low_confidence_and_ambiguous_fields_always_need_review() -> None:
    """Neither weak extraction nor uncertain identity can be accepted silently."""

    record = sample_record(accommodation_confidence=0.84)
    record.goals[0].reconciliation_status = ReconciliationStatus.AMBIGUOUS
    record.field_confidences.annual_review = 0.83
    result = ConfidenceGate(field_threshold=0.85, legibility_threshold=0.7).evaluate(record)

    assert result.state is GateState.NEEDS_REVIEW
    paths = {item.path for item in result.review_fields}
    assert "accommodations[0]" in paths
    assert "goals[0].reconciliation_status" in paths
    assert "dates.annual_review" in paths


def test_one_low_confidence_scope_reference_routes_the_record_to_review() -> None:
    """A partially trusted scope cannot distribute an otherwise trusted accommodation."""

    record = sample_record().model_copy(deep=True)
    record.accommodations[0].applies_to_refs[0].confidence = 0.84

    result = ConfidenceGate(field_threshold=0.85).evaluate(record)

    assert result.state is GateState.NEEDS_REVIEW
    assert "accommodations[0].applies_to_refs[0]" in {item.path for item in result.review_fields}


def test_identical_text_with_different_scope_fingerprints_is_not_deduplicated() -> None:
    """Disjunctive clauses remain distinct even when their action text is identical."""

    original = sample_record().accommodations[0]
    subject_clause = original.model_copy(
        update={
            "id": "22222222-2222-4222-8222-222222222222",
            "applies_to_refs": [
                AccommodationScopeReference(
                    scope=AccommodationScope.SUBJECT,
                    ref="Mathematics",
                    source_page=2,
                    source_quote="in Mathematics",
                    confidence=0.98,
                )
            ],
        }
    )

    assert deduplicate_accommodations([original, subject_clause]) == [
        original,
        subject_clause,
    ]


def test_low_legibility_handwriting_or_stamp_overlap_needs_review() -> None:
    """Unreadable handwriting/stamp overlap cannot hide behind high field confidence."""

    record = sample_record().model_copy(deep=True)
    record.extraction_meta.legibility_scores[1] = 0.41

    result = ConfidenceGate(field_threshold=0.85, legibility_threshold=0.7).evaluate(record)

    assert result.state is GateState.NEEDS_REVIEW
    assert result.review_fields[0].path == "extraction_meta.legibility_scores[1]"


def test_null_source_date_confidence_zero_is_routed_to_review() -> None:
    """Canonical persisted confidence keeps an absent date from silent acceptance."""

    result = ConfidenceGate().evaluate(sample_record())

    review = {item.path: item for item in result.review_fields}
    assert review["dates.last_progress_report"].confidence == 0.0
