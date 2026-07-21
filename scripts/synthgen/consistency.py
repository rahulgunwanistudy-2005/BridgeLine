"""Internal-consistency checks across district ↔ ground truth (and later progress data).

A single failing invariant here would surface as a mysterious bug in the rules-engine,
reconciliation, or dashboard branches, so every cross-reference is asserted explicitly.
Returns a list of human-readable problems; empty means consistent.
"""

from __future__ import annotations

from typing import Any

from synthgen.constants import AS_OF
from synthgen.district import build_district
from synthgen.ground_truth import build_records
from synthgen.progress import SHARMA, SHARMA_EXTENDED_TIME_KEY, build_confirmations
from synthgen.records import validate_scope_references


def check_district_and_ground_truth() -> list[str]:
    problems: list[str] = []
    district = build_district()
    records = list(build_records())

    student_refs = {s["student_ref"] for s in district["students"]}
    holiday_dates = {h["date"] for h in district["calendar"]["holidays"]}

    # 1. Every ground-truth record maps to a known district student, and vice versa.
    record_refs = {r["student_ref"] for r in records}
    if record_refs != student_refs:
        problems.append(f"student/record mismatch: only-district={student_refs - record_refs}, "
                        f"only-records={record_refs - student_refs}")
    if len(records) != 12:
        problems.append(f"expected 12 records, got {len(records)}")

    # 2. Per-record structural expectations from the spec.
    all_ids: list[str] = []
    for r in records:
        sref = r["student_ref"]
        n_acc, n_goal = len(r["accommodations"]), len(r["goals"])
        if not (3 <= n_acc <= 9):
            problems.append(f"{sref}: {n_acc} accommodations (spec 3-9)")
        if not (2 <= n_goal <= 5):
            problems.append(f"{sref}: {n_goal} goals (spec 2-5)")
        if not r["services"]:
            problems.append(f"{sref}: no services")
        page_count = r["extraction_meta"]["page_count"]
        for kind in ("accommodations", "services", "goals"):
            for item in r[kind]:
                all_ids.append(item["id"])
                if not (1 <= item["source_page"] <= page_count):
                    problems.append(f"{sref}: {kind} source_page {item['source_page']} "
                                    f"out of range 1..{page_count}")
                if item["reconciliation_status"] is not None:
                    problems.append(f"{sref}: first extraction must have null reconciliation_status")
                if kind == "accommodations":
                    try:
                        validate_scope_references(item["applies_to_refs"])
                    except ValueError as exc:
                        problems.append(f"{sref}: invalid accommodation scope: {exc}")
                    for reference in item["applies_to_refs"]:
                        if not (1 <= reference["source_page"] <= page_count):
                            problems.append(
                                f"{sref}: scope source_page {reference['source_page']} "
                                f"out of range 1..{page_count}"
                            )

    # 3. Global UUID uniqueness across all authored items.
    if len(all_ids) != len(set(all_ids)):
        problems.append("duplicate item UUIDs detected across records")

    # 4. Required edge cases are actually present.
    problems.extend(_check_edge_cases(records, holiday_dates))

    # 5. Enrollment integrity: every enrollment references a real student and class.
    class_refs = {c["class_ref"] for c in district["classes"]}
    for e in district["enrollments"]:
        if e["student_ref"] not in student_refs:
            problems.append(f"enrollment references unknown student {e['student_ref']}")
        if e["class_ref"] not in class_refs:
            problems.append(f"enrollment references unknown class {e['class_ref']}")

    # 6. Exactly one co-taught class (two teachers of record).
    co_taught = [c for c in district["classes"] if len(c["teachers_of_record"]) >= 2]
    if len(co_taught) != 1:
        problems.append(f"expected exactly 1 co-taught class, found {len(co_taught)}")

    # 7. Exactly one mid-semester enrollment (start after the first instructional day).
    first_day = district["calendar"]["first_instructional_day"]
    late = {e["student_ref"] for e in district["enrollments"] if e["start"] > first_day}
    if len(late) != 1:
        problems.append(f"expected exactly 1 mid-semester enrollee, found {sorted(late)}")

    # 8. Scope semantics and the scripted six-class distribution gate.
    problems.extend(_check_scope_cases(records, district))

    return problems


def _check_scope_cases(records: list[dict[str, Any]], district: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    accommodations = [item for record in records for item in record["accommodations"]]
    scopes = [{reference["scope"] for reference in item["applies_to_refs"]}
              for item in accommodations]
    if not any(scope_set == {"all"} for scope_set in scopes):
        problems.append("no genuinely unconstrained all-scope accommodation")
    if not any(scope_set == {"subject", "context"} for scope_set in scopes):
        problems.append("no subject/context intersection accommodation")
    if not any(
        sum(reference["scope"] == "subject" for reference in item["applies_to_refs"]) > 1
        for item in accommodations
    ):
        problems.append("no same-subject-scope union accommodation")

    academic = [
        reference
        for item in accommodations
        for reference in item["applies_to_refs"]
        if reference["ref"] == "all academic subjects"
    ]
    if len(academic) != 1 or academic[0]["scope"] != "subject" or not (
        0.45 <= academic[0]["confidence"] <= 0.55
    ):
        problems.append("all academic subjects must be one low-confidence subject reference")

    sharma = next(record for record in records if record["student_ref"] == SHARMA)
    extended_time_id = next(
        item["id"]
        for item in sharma["accommodations"]
        if item["text"].startswith("Provide 50% extended time on all classroom tests")
    )
    extended_time = next(
        item for item in sharma["accommodations"] if item["id"] == extended_time_id
    )
    resolved = _resolve_class_refs(SHARMA, extended_time["applies_to_refs"], district)
    expected = {"ENG-101", "MTH-101", "BIO-101", "HIS-101", "PE-101", "ART-101"}
    if resolved != expected:
        problems.append(f"RIV-1001 extended time resolved to {sorted(resolved)}; expected 6 classes")

    confirmations = [
        row
        for row in build_confirmations()
        if row["student_ref"] == SHARMA
        and row["accommodation_key"] == SHARMA_EXTENDED_TIME_KEY
    ]
    confirmation_classes = {row["class_ref"] for row in confirmations}
    confirmed_classes = {row["class_ref"] for row in confirmations if row["confirmed"] == "true"}
    if confirmation_classes != resolved or len(confirmations) != 6:
        problems.append("RIV-1001 confirmation rows do not match the six resolved classes")
    if confirmed_classes != {"ENG-101", "MTH-101", "BIO-101"}:
        problems.append("RIV-1001 extended time is not confirmed in the expected 3 of 6 classes")
    if any(row["accommodation_id"] != extended_time_id for row in confirmations):
        problems.append("RIV-1001 confirmation rows do not carry the stable extended-time ID")
    return problems


def _resolve_class_refs(
    student_ref: str,
    references: list[dict[str, Any]],
    district: dict[str, Any],
) -> set[str]:
    """Resolve document subject phrases for deterministic dataset consistency checks."""

    enrolled = {
        enrollment["class_ref"]
        for enrollment in district["enrollments"]
        if enrollment["student_ref"] == student_ref
    }
    if references[0]["scope"] == "all":
        return enrolled
    subject_refs = {
        " ".join(reference["ref"].split()).casefold()
        for reference in references
        if reference["scope"] == "subject"
    }
    if not subject_refs:
        return enrolled
    subject_names = {
        subject["subject_ref"]: subject["name"].casefold() for subject in district["subjects"]
    }
    resolved_subject_ids = {
        subject_ref for subject_ref, name in subject_names.items() if name in subject_refs
    }
    return {
        class_item["class_ref"]
        for class_item in district["classes"]
        if class_item["class_ref"] in enrolled
        and class_item["subject_ref"] in resolved_subject_ids
    }


def _check_edge_cases(records: list[dict[str, Any]], holiday_dates: set[str]) -> list[str]:
    problems: list[str] = []
    as_of = AS_OF.isoformat()

    overdue = [r["student_ref"] for r in records
               if r["dates"]["annual_review"] and r["dates"]["annual_review"] < as_of]
    if not overdue:
        problems.append("no overdue annual review present")

    triennial_mid = [r["student_ref"] for r in records
                     if r["dates"]["triennial_reeval"]
                     and "2026-08-17" <= r["dates"]["triennial_reeval"] <= "2026-12-18"]
    if not triennial_mid:
        problems.append("no triennial due mid-semester present")

    review_on_holiday = [r["student_ref"] for r in records
                         if r["dates"]["annual_review"] in holiday_dates]
    if not review_on_holiday:
        problems.append("no annual review landing on a holiday present")

    unassigned = [r["student_ref"] for r in records
                  for svc in r["services"] if svc["provider_role"] == "Unassigned"]
    if not unassigned:
        problems.append("no service with an unassigned provider present")

    return problems
