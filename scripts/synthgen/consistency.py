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

    return problems


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
