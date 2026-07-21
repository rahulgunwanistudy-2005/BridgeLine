"""Slice 1 — Deterministic rules-engine derivation suite.

Runs `derive_obligations` against all 12 canonical records, compares output
against hand-authored expected data, and verifies byte-identical determinism
on repeated runs.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field

from bridgeline.rules.engine import derive_obligations

from harness.config import EXPECTED_DIR
from harness.loader import (
    build_approved_record,
    build_roster_snapshot,
    load_canonical_records,
)


@dataclass
class RecordResult:
    """Result from one canonical record derivation."""

    student_ref: str
    expected_obligations: int = 0
    actual_obligations: int = 0
    expected_findings: int = 0
    actual_findings: int = 0
    expected_deadlines: int = 0
    actual_deadlines: int = 0
    obligation_match: bool = False
    finding_match: bool = False
    deadline_match: bool = False
    deterministic: bool = False
    error: str | None = None
    mismatches: list[str] = field(default_factory=list)


@dataclass
class RulesSuiteResult:
    """Aggregate result for the entire rules suite."""

    records: list[RecordResult] = field(default_factory=list)
    determinism_hash: str = ""
    elapsed_seconds: float = 0.0
    passed: bool = False

    @property
    def total_records(self) -> int:
        return len(self.records)

    @property
    def passed_records(self) -> int:
        return sum(
            1 for r in self.records if r.obligation_match and r.finding_match and r.deterministic
        )

    @property
    def failed_records(self) -> int:
        return self.total_records - self.passed_records


def _serialize_obligations(result: object) -> str:
    """Serialize a DerivationResult to a stable JSON string for hashing."""

    obligations = [
        {
            "assignee_ref": o.assignee_ref,
            "assignee_kind": o.assignee_kind.value,
            "rule_id": o.rule_id,
            "citation": o.citation,
            "source_kind": o.source_kind.value,
            "source_ref": str(o.source_ref),
            "context_ref": o.context_ref,
            "context_kind": o.context_kind.value,
            "subject": o.subject,
            "action_text": o.action_text[:120],
        }
        for o in result.obligations
    ]
    findings = [
        {
            "rule_id": f.rule_id,
            "finding_type": f.finding_type,
            "severity": f.severity.value,
            "title": f.title,
            "detail": f.detail[:200],
            "measurements": f.measurements,
        }
        for f in result.findings
    ]
    deadlines = [
        {
            "rule_id": d.rule_id,
            "citation": d.citation,
            "status": d.status.value,
            "description": d.description,
            "legal_due_on": d.legal_due_on.isoformat(),
        }
        for d in result.deadlines
    ]
    return json.dumps(
        {"obligations": obligations, "findings": findings, "deadlines": deadlines},
        sort_keys=True,
        ensure_ascii=False,
    )


def _load_expected(student_ref: str) -> dict | None:
    """Load expected obligations for one student."""

    path = EXPECTED_DIR / f"{student_ref}.obligations.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _compare_obligations(expected: list[dict], actual: list[dict]) -> list[str]:
    """Compare obligation lists by key fields, return mismatch descriptions."""

    mismatches = []

    def _key(o: dict) -> tuple:
        return (o["assignee_ref"], o["rule_id"], o["source_ref"], o["context_ref"])

    expected_set = {_key(o) for o in expected}
    actual_set = {_key(o) for o in actual}

    missing = expected_set - actual_set
    extra = actual_set - expected_set

    for m in sorted(missing):
        mismatches.append(f"MISSING obligation: assignee={m[0]} rule={m[1]} source={m[2]}")
    for e in sorted(extra):
        mismatches.append(f"EXTRA obligation: assignee={e[0]} rule={e[1]} source={e[2]}")

    return mismatches


def _compare_findings(expected: list[dict], actual: list[dict]) -> list[str]:
    """Compare finding lists by key fields."""

    mismatches = []

    def _key(f: dict) -> tuple:
        return (f["rule_id"], f["finding_type"], f.get("title", ""))

    expected_set = {_key(f) for f in expected}
    actual_set = {_key(f) for f in actual}

    missing = expected_set - actual_set
    extra = actual_set - expected_set

    for m in sorted(missing):
        mismatches.append(f"MISSING finding: rule={m[0]} type={m[1]}")
    for e in sorted(extra):
        mismatches.append(f"EXTRA finding: rule={e[0]} type={e[1]}")

    return mismatches


def run(*, verbose: bool = False) -> RulesSuiteResult:
    """Run the full rules derivation suite."""

    suite = RulesSuiteResult()
    start = time.monotonic()
    all_serialized: list[str] = []

    records = load_canonical_records()
    print(f"\n{'='*60}")
    print(f"  RULES SUITE — {len(records)} canonical records")
    print(f"{'='*60}\n")

    for record in records:
        rr = RecordResult(student_ref=record.student_ref)

        expected = _load_expected(record.student_ref)
        if expected is None:
            rr.error = f"No expected file for {record.student_ref}"
            suite.records.append(rr)
            print(f"  ✗ {record.student_ref}: {rr.error}")
            continue

        try:
            approved = build_approved_record(record)
            roster = build_roster_snapshot(record)

            # First derivation
            result1 = derive_obligations(approved, roster)
            serialized1 = _serialize_obligations(result1)

            # Second derivation — determinism check
            result2 = derive_obligations(approved, roster)
            serialized2 = _serialize_obligations(result2)

            rr.deterministic = serialized1 == serialized2
            all_serialized.append(serialized1)

            # Build actual summaries for comparison
            actual_obligations = [
                {
                    "assignee_ref": o.assignee_ref,
                    "assignee_kind": o.assignee_kind.value,
                    "rule_id": o.rule_id,
                    "citation": o.citation,
                    "source_kind": o.source_kind.value,
                    "source_ref": str(o.source_ref),
                    "context_ref": o.context_ref,
                    "context_kind": o.context_kind.value,
                    "subject": o.subject,
                    "action_text": o.action_text[:120],
                }
                for o in result1.obligations
            ]
            actual_findings = [
                {
                    "rule_id": f.rule_id,
                    "finding_type": f.finding_type,
                    "severity": f.severity.value,
                    "title": f.title,
                    "detail": f.detail[:200],
                    "measurements": f.measurements,
                }
                for f in result1.findings
            ]

            rr.expected_obligations = expected["obligation_count"]
            rr.actual_obligations = len(result1.obligations)
            rr.expected_findings = expected["finding_count"]
            rr.actual_findings = len(result1.findings)
            rr.expected_deadlines = expected["deadline_count"]
            rr.actual_deadlines = len(result1.deadlines)

            obl_mismatches = _compare_obligations(
                expected["obligations"], actual_obligations
            )
            find_mismatches = _compare_findings(
                expected["findings"], actual_findings
            )

            rr.obligation_match = len(obl_mismatches) == 0
            rr.finding_match = len(find_mismatches) == 0
            rr.deadline_match = rr.expected_deadlines == rr.actual_deadlines
            rr.mismatches = obl_mismatches + find_mismatches

        except Exception as exc:
            rr.error = str(exc)

        suite.records.append(rr)

        # Print result
        status = "✓" if (rr.obligation_match and rr.finding_match and rr.deterministic) else "✗"
        det = "DET" if rr.deterministic else "NON-DET"
        print(
            f"  {status} {record.student_ref}: "
            f"{rr.actual_obligations}/{rr.expected_obligations} oblig, "
            f"{rr.actual_findings}/{rr.expected_findings} find, "
            f"{rr.actual_deadlines}/{rr.expected_deadlines} dead — "
            f"[{det}]"
        )
        if rr.error:
            print(f"    ERROR: {rr.error}")
        if verbose and rr.mismatches:
            for m in rr.mismatches[:5]:
                print(f"    {m}")
            if len(rr.mismatches) > 5:
                print(f"    ... and {len(rr.mismatches) - 5} more")

    suite.elapsed_seconds = time.monotonic() - start

    # Compute determinism hash across all records
    combined = "\n".join(all_serialized)
    suite.determinism_hash = hashlib.sha256(combined.encode()).hexdigest()

    suite.passed = suite.failed_records == 0
    print(f"\n  {suite.passed_records}/{suite.total_records} passed")
    print(f"  Determinism hash: {suite.determinism_hash[:16]}")
    print(f"  Elapsed: {suite.elapsed_seconds:.2f}s")
    result_emoji = "✓ PASS" if suite.passed else "✗ FAIL"
    print(f"\n  Rules Suite: {result_emoji}\n")
    return suite
