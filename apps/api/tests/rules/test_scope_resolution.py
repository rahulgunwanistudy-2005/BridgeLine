"""Deterministic scope resolution and fail-closed finding tests."""

from bridgeline.db.schemas import AccommodationScope, AccommodationScopeReference
from bridgeline.rules.engine import derive_obligations
from bridgeline.rules.scope_resolution import resolve_scope
from bridgeline.rules.types import (
    ApprovedRecord,
    RosterClass,
    RosterSnapshot,
    ScopeMappingKind,
    ScopeReferenceMapping,
    TeacherAssignment,
)


def _reference(scope: AccommodationScope, ref: str) -> AccommodationScopeReference:
    return AccommodationScopeReference(
        scope=scope,
        ref=ref,
        source_page=5,
        source_quote=f"approved {ref}",
        confidence=0.98,
    )


def _with_refs(
    approved: ApprovedRecord, *references: AccommodationScopeReference
) -> ApprovedRecord:
    accommodation = approved.record.accommodations[0].model_copy(
        update={"applies_to_refs": list(references)}
    )
    return approved.model_copy(
        update={"record": approved.record.model_copy(update={"accommodations": [accommodation]})}
    )


def test_context_only_scope_fans_to_every_class_after_alias_resolution(
    approved_record: ApprovedRecord, roster: RosterSnapshot
) -> None:
    scoped = _with_refs(
        approved_record, _reference(AccommodationScope.CONTEXT, "  During\u00a0Testing ")
    )
    mapped = roster.model_copy(
        update={
            "scope_mappings": (
                ScopeReferenceMapping(
                    scope=AccommodationScope.CONTEXT,
                    document_ref="during testing",
                    target_ref="assessment",
                    kind=ScopeMappingKind.DISTRICT_ALIAS,
                ),
            )
        }
    )

    resolution = resolve_scope(scoped.record.accommodations[0], mapped)

    assert not resolution.issues
    assert {item.classroom.class_ref for item in resolution.classes} == {
        "class-ela",
        "class-math",
    }


def test_subject_and_context_scopes_intersect(
    approved_record: ApprovedRecord, roster: RosterSnapshot
) -> None:
    scoped = _with_refs(
        approved_record,
        _reference(AccommodationScope.SUBJECT, "mathematics"),
        _reference(AccommodationScope.CONTEXT, "during testing"),
    )
    mapped = roster.model_copy(
        update={
            "scope_mappings": (
                ScopeReferenceMapping(
                    scope=AccommodationScope.CONTEXT,
                    document_ref="during testing",
                    target_ref="assessment",
                    kind=ScopeMappingKind.DISTRICT_ALIAS,
                ),
            )
        }
    )

    resolution = resolve_scope(scoped.record.accommodations[0], mapped)

    assert [item.classroom.class_ref for item in resolution.classes] == ["class-math"]
    assert {item.scope for item in resolution.classes[0].provenance} == {
        AccommodationScope.SUBJECT,
        AccommodationScope.CONTEXT,
    }


def test_unresolved_scope_emits_finding_instead_of_guessing(
    approved_record: ApprovedRecord, roster: RosterSnapshot
) -> None:
    scoped = _with_refs(
        approved_record, _reference(AccommodationScope.SUBJECT, "all academic subjects")
    )

    result = derive_obligations(scoped, roster)

    accommodation_id = scoped.record.accommodations[0].id
    assert not any(item.source_ref == accommodation_id for item in result.obligations)
    assert [
        item.finding_type
        for item in result.findings
        if item.finding_type.startswith("scope-reference-")
    ] == ["scope-reference-unresolved"]


def test_multiple_roster_matches_are_ambiguous_and_never_pick_first(
    approved_record: ApprovedRecord, roster: RosterSnapshot
) -> None:
    scoped = _with_refs(approved_record, _reference(AccommodationScope.SUBJECT, "Mathematics"))
    duplicate_subject = RosterClass(
        class_ref="class-math-lab",
        subject="MATHEMATICS",
        teachers=(TeacherAssignment(teacher_ref="teacher-lab"),),
    )
    ambiguous_roster = roster.model_copy(update={"classes": (*roster.classes, duplicate_subject)})

    result = derive_obligations(scoped, ambiguous_roster)

    accommodation_id = scoped.record.accommodations[0].id
    assert not any(item.source_ref == accommodation_id for item in result.obligations)
    assert [
        item.finding_type
        for item in result.findings
        if item.finding_type.startswith("scope-reference-")
    ] == ["scope-reference-ambiguous"]
