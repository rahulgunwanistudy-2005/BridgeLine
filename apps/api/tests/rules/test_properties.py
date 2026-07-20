"""Property-based invariants for deterministic rule derivation and persistence."""

import hashlib
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from bridgeline.db.schemas import AccommodationScope, AccommodationScopeReference
from bridgeline.rules.citations import parse_citations
from bridgeline.rules.engine import (
    RuleInvariantError,
    _validate_obligations,
    derive_obligations,
)
from bridgeline.rules.repository import _unseen_obligations
from bridgeline.rules.types import (
    ApprovedRecord,
    RosterClass,
    RosterSnapshot,
    TeacherAssignment,
)

PROPERTY_SETTINGS = settings(
    max_examples=40,
    deadline=None,
    suppress_health_check=(HealthCheck.function_scoped_fixture,),
)


def _scoped_inputs(
    approved: ApprovedRecord,
    roster: RosterSnapshot,
    *,
    accommodation_text: str,
    class_count: int,
) -> tuple[ApprovedRecord, RosterSnapshot]:
    accommodation = approved.record.accommodations[0].model_copy(
        update={
            "text": accommodation_text,
            "applies_to_refs": [
                AccommodationScopeReference(
                    scope=AccommodationScope.ALL,
                    ref="across all classes",
                    source_page=2,
                    source_quote="approved across all classes",
                    confidence=1.0,
                )
            ],
        }
    )
    record = approved.record.model_copy(update={"accommodations": [accommodation]})
    classes = tuple(
        RosterClass(
            class_ref=f"class-{index:02d}",
            subject=f"Subject {index:02d}",
            teachers=(TeacherAssignment(teacher_ref=f"teacher-{index:02d}"),),
        )
        for index in range(class_count)
    )
    return (
        approved.model_copy(update={"record": record}),
        roster.model_copy(update={"classes": classes}),
    )


@PROPERTY_SETTINGS
@given(
    accommodation_text=st.text(min_size=1, max_size=300),
    class_count=st.integers(min_value=1, max_value=6),
)
def test_identical_frozen_inputs_are_canonical_and_byte_identical(
    approved_record: ApprovedRecord,
    roster: RosterSnapshot,
    accommodation_text: str,
    class_count: int,
) -> None:
    approved, scoped_roster = _scoped_inputs(
        approved_record,
        roster,
        accommodation_text=accommodation_text,
        class_count=class_count,
    )

    first = derive_obligations(approved, scoped_roster)
    second = derive_obligations(approved, scoped_roster)
    first_bytes = first.model_dump_json().encode()
    second_bytes = second.model_dump_json().encode()

    assert first_bytes == second_bytes
    assert hashlib.sha256(first_bytes).digest() == hashlib.sha256(second_bytes).digest()
    assert tuple(str(item.id) for item in first.obligations) == tuple(
        str(item.id) for item in second.obligations
    )


@PROPERTY_SETTINGS
@given(
    accommodation_text=st.text(min_size=1, max_size=300),
    class_count=st.integers(min_value=1, max_value=8),
)
def test_accommodation_never_has_zero_obligations_when_a_class_exists(
    approved_record: ApprovedRecord,
    roster: RosterSnapshot,
    accommodation_text: str,
    class_count: int,
) -> None:
    approved, scoped_roster = _scoped_inputs(
        approved_record,
        roster,
        accommodation_text=accommodation_text,
        class_count=class_count,
    )

    result = derive_obligations(approved, scoped_roster)
    accommodation_id = approved.record.accommodations[0].id

    assert any(item.source_ref == accommodation_id for item in result.obligations)


@PROPERTY_SETTINGS
@given(scope_ref=st.sampled_from(["Mathematics", "Unknown academic area"]))
def test_scoped_accommodation_emits_obligation_or_explicit_review_finding(
    approved_record: ApprovedRecord,
    roster: RosterSnapshot,
    scope_ref: str,
) -> None:
    """An unresolvable scope cannot disappear silently or broaden to all classes."""

    accommodation = approved_record.record.accommodations[0].model_copy(
        update={
            "applies_to_refs": [
                AccommodationScopeReference(
                    scope=AccommodationScope.SUBJECT,
                    ref=scope_ref,
                    source_page=2,
                    source_quote=f"approved in {scope_ref}",
                    confidence=1.0,
                )
            ]
        }
    )
    approved = approved_record.model_copy(
        update={
            "record": approved_record.record.model_copy(update={"accommodations": [accommodation]})
        }
    )

    result = derive_obligations(approved, roster)
    emitted = any(item.source_ref == accommodation.id for item in result.obligations)
    review = any(
        item.finding_type.startswith("scope-reference-")
        and item.related_refs.get("accommodation_id") == str(accommodation.id)
        for item in result.findings
    )

    assert emitted is not review


@PROPERTY_SETTINGS
@given(class_count=st.integers(min_value=1, max_value=8))
def test_persistence_filter_is_idempotent(
    approved_record: ApprovedRecord,
    roster: RosterSnapshot,
    class_count: int,
) -> None:
    approved, scoped_roster = _scoped_inputs(
        approved_record,
        roster,
        accommodation_text="Provide extended time.",
        class_count=class_count,
    )
    obligations = derive_obligations(approved, scoped_roster).obligations

    first_insert = _unseen_obligations(set(), obligations)
    persisted_ids = {item.id for item in first_insert}
    second_insert = _unseen_obligations(persisted_ids, obligations)

    assert first_insert == obligations
    assert second_insert == ()


@PROPERTY_SETTINGS
@given(class_count=st.integers(min_value=1, max_value=6))
def test_every_emitted_obligation_uses_exact_human_owned_citation(
    approved_record: ApprovedRecord,
    roster: RosterSnapshot,
    class_count: int,
) -> None:
    approved, scoped_roster = _scoped_inputs(
        approved_record,
        roster,
        accommodation_text="Use the approved support.",
        class_count=class_count,
    )
    citations_path = Path(__file__).resolve().parents[4] / "references" / "idea-citations.md"
    citations = parse_citations(citations_path.read_text(encoding="utf-8"))

    obligations = derive_obligations(approved, scoped_roster).obligations

    assert all(citations[item.rule_id] == item.citation for item in obligations)


@PROPERTY_SETTINGS
@given(class_count=st.integers(min_value=1, max_value=8))
def test_obligation_order_is_stable_and_canonical(
    approved_record: ApprovedRecord,
    roster: RosterSnapshot,
    class_count: int,
) -> None:
    approved, scoped_roster = _scoped_inputs(
        approved_record,
        roster,
        accommodation_text="Provide the approved accommodation.",
        class_count=class_count,
    )
    obligations = derive_obligations(approved, scoped_roster).obligations
    keys = tuple(
        (
            item.assignee_kind.value,
            item.assignee_ref,
            item.context_kind.value,
            item.context_ref,
            item.rule_id,
            item.source_kind.value,
            str(item.source_ref),
        )
        for item in obligations
    )

    assert keys == tuple(sorted(keys))


@PROPERTY_SETTINGS
@given(class_count=st.integers(min_value=1, max_value=6))
def test_invariant_rejects_fabricated_citation(
    approved_record: ApprovedRecord,
    roster: RosterSnapshot,
    class_count: int,
) -> None:
    approved, scoped_roster = _scoped_inputs(
        approved_record,
        roster,
        accommodation_text="Provide the approved accommodation.",
        class_count=class_count,
    )
    obligations = derive_obligations(approved, scoped_roster).obligations
    corrupted = (
        obligations[0].model_copy(update={"citation": "not-a-regulation-citation"}),
        *obligations[1:],
    )

    with pytest.raises(RuleInvariantError, match="unregistered rule provenance"):
        _validate_obligations(approved, scoped_roster, corrupted, ())
