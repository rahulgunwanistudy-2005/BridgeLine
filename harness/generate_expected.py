#!/usr/bin/env python3
"""Generate expected obligation summaries by running the rules engine on canonical data.

Run this ONCE to populate harness/expected/, then hand-verify the output.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from harness.loader import (
    build_approved_record,
    build_roster_snapshot,
    load_canonical_records,
)

from bridgeline.rules.engine import derive_obligations


def main() -> None:
    expected_dir = Path(__file__).resolve().parent / "expected"
    expected_dir.mkdir(exist_ok=True)

    records = load_canonical_records()
    print(f"Generating expected obligations for {len(records)} records...")

    for record in records:
        approved = build_approved_record(record)
        roster = build_roster_snapshot(record)
        try:
            result = derive_obligations(approved, roster)
        except Exception as exc:
            print(f"  {record.student_ref}: ERROR — {exc}")
            continue

        summary = {
            "student_ref": record.student_ref,
            "rules_version": result.rules_version,
            "obligation_count": len(result.obligations),
            "deadline_count": len(result.deadlines),
            "finding_count": len(result.findings),
            "obligations": [
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
            ],
            "findings": [
                {
                    "rule_id": f.rule_id,
                    "finding_type": f.finding_type,
                    "severity": f.severity.value,
                    "title": f.title,
                    "detail": f.detail[:200],
                    "measurements": f.measurements,
                }
                for f in result.findings
            ],
            "deadlines": [
                {
                    "rule_id": d.rule_id,
                    "citation": d.citation,
                    "status": d.status.value,
                    "description": d.description,
                    "legal_due_on": d.legal_due_on.isoformat(),
                }
                for d in result.deadlines
            ],
        }

        out_path = expected_dir / f"{record.student_ref}.obligations.json"
        out_path.write_text(
            json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(
            f"  {record.student_ref}: "
            f"{len(result.obligations)} obligations, "
            f"{len(result.findings)} findings, "
            f"{len(result.deadlines)} deadlines"
        )

    print("Done.")


if __name__ == "__main__":
    main()
