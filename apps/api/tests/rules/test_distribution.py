"""Unit tests for each Family-1 distribution rule."""

from bridgeline.db.schemas import AccommodationScope, AccommodationScopeReference
from bridgeline.rules.families.distribution import (
    TeacherAccessRule,
    TeacherAccommodationsRule,
    TeacherResponsibilitiesRule,
)
from bridgeline.rules.types import ApprovedRecord, RosterSnapshot, RuleState, SourceKind


def test_teacher_access_is_one_per_unique_teacher_and_provider(
    approved_record: ApprovedRecord, roster: RosterSnapshot
) -> None:
    obligations = TeacherAccessRule().derive(approved_record, roster)

    assert {item.assignee_ref for item in obligations} == {
        "teacher-ela",
        "teacher-math",
        "teacher-math-co",
        "provider-sped",
    }
    assert all(item.source_kind is SourceKind.IEP_RECORD for item in obligations)


def test_responsibilities_include_each_class_and_assigned_service(
    approved_record: ApprovedRecord, roster: RosterSnapshot
) -> None:
    obligations = TeacherResponsibilitiesRule().derive(approved_record, roster)

    assert len(obligations) == 4
    assert {item.context_ref for item in obligations} == {
        "class-ela",
        "class-math",
        str(approved_record.record.services[0].id),
    }
    assert (
        TeacherResponsibilitiesRule().check(RuleState(approved=approved_record, roster=roster))
        == ()
    )


def test_missing_service_provider_is_an_explicit_cited_finding(
    approved_record: ApprovedRecord, roster: RosterSnapshot
) -> None:
    empty = roster.model_copy(update={"providers": ()})

    findings = TeacherResponsibilitiesRule().check(
        RuleState(approved=approved_record, roster=empty)
    )

    assert len(findings) == 1
    assert findings[0].finding_type == "service-provider-unassigned"
    assert findings[0].citation == "34 CFR §300.323(d)(2)(i)"


def test_all_context_accommodation_fans_out_to_coteachers(
    approved_record: ApprovedRecord, roster: RosterSnapshot
) -> None:
    obligations = TeacherAccommodationsRule().derive(approved_record, roster)

    assert len(obligations) == 3
    assert {item.assignee_ref for item in obligations} == {
        "teacher-ela",
        "teacher-math",
        "teacher-math-co",
    }
    assert all(
        item.action_text == approved_record.record.accommodations[0].text for item in obligations
    )


def test_subject_scope_targets_only_matching_subject(
    approved_record: ApprovedRecord, roster: RosterSnapshot
) -> None:
    accommodation = approved_record.record.accommodations[0].model_copy(
        update={
            "applies_to_refs": [
                AccommodationScopeReference(
                    scope=AccommodationScope.SUBJECT,
                    ref="Mathematics",
                    source_page=2,
                    source_quote="in Mathematics",
                    confidence=1.0,
                )
            ]
        }
    )
    scoped = approved_record.model_copy(
        update={
            "record": approved_record.record.model_copy(update={"accommodations": [accommodation]})
        }
    )

    obligations = TeacherAccommodationsRule().derive(scoped, roster)

    assert {item.assignee_ref for item in obligations} == {"teacher-math", "teacher-math-co"}
    assert {item.scope_provenance[0].ref for item in obligations} == {"Mathematics"}
