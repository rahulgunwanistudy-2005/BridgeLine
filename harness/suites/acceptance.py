"""Slice 3 — E2E acceptance suite for the three scripted Riverside findings.

Verifies that the safety architecture produces the exact expected results on
known-signal data: the Sharma Goal 2 conflict (data-level), the extended-time
3-of-6 gap (rules engine), and the service −20 min/wk variance (rules engine).
"""

from __future__ import annotations

import csv
import json
import time
from dataclasses import dataclass, field
from uuid import UUID

from bridgeline.rules.families.distribution import TeacherAccommodationsRule
from bridgeline.rules.families.minutes import ServicesStatementRule
from bridgeline.rules.types import RuleState

from harness.config import PROGRESS_DIR
from harness.loader import (
    build_approved_record,
    build_roster_snapshot,
    load_record,
)


@dataclass
class FindingResult:
    """Result from one scripted finding assertion."""

    name: str
    passed: bool = False
    expected: str = ""
    actual: str = ""
    detail: str = ""


@dataclass
class AcceptanceSuiteResult:
    """Aggregate result for the acceptance suite."""

    findings: list[FindingResult] = field(default_factory=list)
    elapsed_seconds: float = 0.0
    passed: bool = False

    @property
    def total_findings(self) -> int:
        return len(self.findings)

    @property
    def passed_findings(self) -> int:
        return sum(1 for f in self.findings if f.passed)


def _check_sharma_goal_2_conflict() -> FindingResult:
    """Finding (a): gradebook vs teacher-note conflict for RIV-1001 Goal 2.

    RIV-1001 (A. Sharma) has gradebook data showing ~40% on g2-comprehension
    assessments, while teacher note TN-0001 says "doing well".
    """

    fr = FindingResult(
        name="Sharma Goal 2 conflict",
        expected="Gradebook avg ~40% but teacher note says 'doing well'",
    )

    # Load gradebook
    gradebook_path = PROGRESS_DIR / "gradebook" / "ENG-101.csv"
    with gradebook_path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    goal_rows = [
        row for row in rows
        if row["student_ref"] == "RIV-1001"
        and row["iep_goal_key"] == "g2-comprehension"
    ]

    if not goal_rows:
        fr.actual = "No g2-comprehension gradebook rows found for RIV-1001"
        return fr

    scores = [int(row["percent"]) for row in goal_rows]
    avg = sum(scores) / len(scores)

    # Load teacher notes
    notes_path = PROGRESS_DIR / "teacher_notes" / "teacher_notes.json"
    notes = json.loads(notes_path.read_text(encoding="utf-8"))
    tn_0001 = next(
        (n for n in notes if n["note_id"] == "TN-0001" and n["student_ref"] == "RIV-1001"),
        None,
    )

    if tn_0001 is None:
        fr.actual = "TN-0001 teacher note not found for RIV-1001"
        return fr

    note_text = tn_0001["text"]
    note_says_well = "doing well" in note_text.lower()

    # Assert the conflict
    if 35 <= avg <= 45 and note_says_well:
        fr.passed = True
        fr.actual = (
            f"Gradebook avg {avg:.0f}% across {len(scores)} assessments; "
            f"teacher note says 'doing well' — conflict confirmed"
        )
    else:
        fr.actual = f"Gradebook avg {avg:.0f}%, note_says_well={note_says_well}"

    fr.detail = (
        f"Goal: {tn_0001['iep_goal_key']} ({tn_0001['iep_goal_id']})\n"
        f"Assessments: {len(scores)} rows, scores: {scores}\n"
        f"Teacher note: \"{note_text[:100]}...\""
    )
    return fr


def _check_extended_time_3_of_6() -> FindingResult:
    """Finding (b): extended-time accommodation confirmed in 3 of 6 classes.

    Uses the rules engine's TeacherAccommodationsRule.check() to verify
    the partial-confirmation finding fires.
    """

    fr = FindingResult(
        name="Extended-time 3-of-6 gap",
        expected="accommodation-partially-confirmed: confirmed in 3 of 6 classes",
    )

    record = load_record("RIV-1001")
    approved = build_approved_record(record)
    roster = build_roster_snapshot(record, include_confirmations=True)

    accommodation_id = UUID("3b341238-caab-51d4-8b11-a3913e1fa7d7")

    # Verify the accommodation confirmations look right
    student_states = [
        s for s in roster.accommodation_classes
        if s.accommodation_id == accommodation_id
    ]

    if len(student_states) != 6:
        fr.actual = f"Expected 6 AccommodationClassState rows, got {len(student_states)}"
        return fr

    confirmed = {s.class_ref for s in student_states if s.confirmed}
    unconfirmed = {s.class_ref for s in student_states if not s.confirmed}

    if confirmed != {"ENG-101", "MTH-101", "BIO-101"}:
        fr.actual = f"Confirmed set mismatch: {confirmed}"
        return fr

    if unconfirmed != {"HIS-101", "PE-101", "ART-101"}:
        fr.actual = f"Unconfirmed set mismatch: {unconfirmed}"
        return fr

    # Now run the rules check
    state = RuleState(approved=approved, roster=roster)
    findings = TeacherAccommodationsRule().check(state)

    partial_findings = [
        f for f in findings
        if f.finding_type == "accommodation-partially-confirmed"
    ]

    if not partial_findings:
        fr.actual = "No accommodation-partially-confirmed finding produced"
        fr.detail = f"Total findings from check(): {len(findings)}"
        return fr

    finding = partial_findings[0]

    expected_title = (
        "Provide 50% extended time on all classroom tests and quizzes. "
        "is confirmed in 3 of 6 classes; 3 classes remain unconfirmed."
    )

    if finding.title != expected_title:
        fr.actual = f"Title mismatch: '{finding.title}'"
        return fr

    expected_measurements = {
        "confirmed_classes": 3,
        "total_classes": 6,
        "unconfirmed_classes": 3,
    }

    if finding.measurements != expected_measurements:
        fr.actual = f"Measurements mismatch: {finding.measurements}"
        return fr

    fr.passed = True
    fr.actual = (
        f"Finding fires: {finding.title[:80]}... "
        f"Measurements: {finding.measurements}"
    )
    fr.detail = f"Severity: {finding.severity.value}, Rule: {finding.rule_id}"
    return fr


def _check_service_variance() -> FindingResult:
    """Finding (c): RIV-1002 SAI delivered 130 min/wk vs 150 mandated = −20 min/wk.

    Uses the rules engine's ServicesStatementRule.check() to verify
    the service-minute-variance finding fires with negative variance.
    """

    fr = FindingResult(
        name="Service −20 min/wk variance",
        expected="service-minute-variance with negative variance for RIV-1002 SAI",
    )

    record = load_record("RIV-1002")
    approved = build_approved_record(record)
    roster = build_roster_snapshot(record, include_service_logs=True)

    state = RuleState(approved=approved, roster=roster)
    findings = ServicesStatementRule().check(state)

    variance_findings = [
        f for f in findings
        if f.finding_type == "service-minute-variance"
    ]

    if not variance_findings:
        all_types = [f.finding_type for f in findings]
        fr.actual = f"No service-minute-variance finding produced. Types: {all_types}"
        return fr

    # Find the SAI-related variance findings with negative variance
    sai_service_id = str(record.services[0].id)  # "Specialized academic instruction"
    negative_findings = [
        f for f in variance_findings
        if f.measurements.get("variance_minutes", 0) < 0
        and f.related_refs.get("service_id") == sai_service_id
    ]

    if not negative_findings:
        fr.actual = (
            f"No negative-variance findings for SAI service. "
            f"Total variance findings: {len(variance_findings)}"
        )
        fr.detail = "\n".join(
            f"  {f.title}: variance={f.measurements.get('variance_minutes')}"
            for f in variance_findings[:5]
        )
        return fr

    # Check that the deficit is ~20 min/wk
    sample = negative_findings[0]
    variance = sample.measurements.get("variance_minutes", 0)

    if abs(variance + 20) > 1:
        fr.actual = f"Variance is {variance}, expected ~-20"
        return fr

    fr.passed = True
    fr.actual = (
        f"{len(negative_findings)} weeks short. "
        f"Sample: {sample.title} (variance={variance})"
    )
    fr.detail = (
        f"Service: {record.services[0].type}\n"
        f"Mandated: {record.services[0].minutes_per_week} min/wk\n"
        f"Measurements: {sample.measurements}"
    )
    return fr


def run(*, verbose: bool = False) -> AcceptanceSuiteResult:
    """Run the three scripted acceptance assertions."""

    suite = AcceptanceSuiteResult()
    start = time.monotonic()

    print(f"\n{'='*60}")
    print("  ACCEPTANCE SUITE — 3 scripted findings")
    print(f"{'='*60}\n")

    checks = [
        _check_sharma_goal_2_conflict,
        _check_extended_time_3_of_6,
        _check_service_variance,
    ]

    for check_fn in checks:
        result = check_fn()
        suite.findings.append(result)

        status = "✓" if result.passed else "✗"
        print(f"  {status} {result.name}")
        print(f"    Expected: {result.expected}")
        print(f"    Actual:   {result.actual}")
        if verbose and result.detail:
            for line in result.detail.split("\n"):
                print(f"    {line}")

    suite.elapsed_seconds = time.monotonic() - start
    suite.passed = suite.passed_findings == suite.total_findings

    print(f"\n  {suite.passed_findings}/{suite.total_findings} passed")
    print(f"  Elapsed: {suite.elapsed_seconds:.2f}s")
    result_emoji = "✓ PASS" if suite.passed else "✗ FAIL"
    print(f"\n  Acceptance Suite: {result_emoji}\n")
    return suite
