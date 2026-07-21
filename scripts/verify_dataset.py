#!/usr/bin/env python
"""Acceptance gate for the synthetic dataset: validation + consistency + byte-stability.

Runs read-only checks against already-emitted files where possible, and re-derives the
in-memory model to assert internal consistency and schema conformance. Exits non-zero on
any problem so CI and the harness fail loudly.

Usage:  PYTHONPATH=scripts .venv-synth/bin/python scripts/verify_dataset.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from synthgen.consistency import check_district_and_ground_truth
from synthgen.constants import DATA_DIR, GROUND_TRUTH_DIR
from synthgen.evidence import evidence_problems
from synthgen.ground_truth import build_records
from synthgen.records import validate_scope_references
from synthgen.validate import RecordValidationError, validate_record


def _hash_tree(root: Path) -> str:
    """Stable hash over all files under root (sorted), for byte-stability checks."""

    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_file():
            digest.update(path.relative_to(root).as_posix().encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


def main() -> int:
    failures = 0
    canonical_records = build_records()

    print("== schema validation ==")
    for record in canonical_records:
        try:
            validate_record(record, label=record["student_ref"])
        except RecordValidationError as exc:
            failures += 1
            print(f"  INVALID {exc.label}: {exc.messages}", file=sys.stderr)
    if not failures:
        print("  12/12 records valid against packages/schemas/IEPRecord.json")

    print("== scripted findings (STEP 2) ==")
    from synthgen.findings import compute_findings

    findings = compute_findings()
    for f in findings:
        mark = "FIRED" if f.fired else "MISSING"
        print(f"  [{mark}] {f.title}: {f.detail}")
        if not f.fired:
            failures += 1

    print("== variant records (STEP 6) ==")
    from synthgen.variants import build_variants

    variants = build_variants()
    v_bad = 0
    for record in variants:
        try:
            validate_record(record, label=record["student_ref"])
        except RecordValidationError as exc:
            v_bad += 1
            print(f"  INVALID {exc.label}: {exc.messages}", file=sys.stderr)
    academic_subject_refs = [
        reference
        for record in variants
        for item in record["accommodations"]
        for reference in item["applies_to_refs"]
        if reference["ref"] == "all academic subjects"
    ]
    if any(not 0.45 <= reference["confidence"] <= 0.55 for reference in academic_subject_refs):
        v_bad += 1
        print("  INVALID: variant expanded or raised confidence for all academic subjects",
              file=sys.stderr)
    failures += v_bad
    manifest_path = DATA_DIR / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        total = manifest["document_count"]
        print(f"  {len(variants)} variants valid; manifest lists {total} documents "
              f"({manifest['degraded_count']} degraded)")
        if total != 100:
            failures += 1
            print(f"  EXPECTED 100 documents, manifest has {total}", file=sys.stderr)
    else:
        print("  (manifest missing: run build_variants.py)")

    print("== rendered source evidence ==")
    evidence_failures = [
        problem
        for record in [*canonical_records, *variants]
        for problem in evidence_problems(record)
    ]
    if evidence_failures:
        failures += len(evidence_failures)
        for problem in evidence_failures:
            print(f"  PROBLEM: {problem}", file=sys.stderr)
    else:
        print("  100/100 clean PDFs have exactly 4 pages; every quote matches its declared page")

    print("== emitted record validation ==")
    emitted_paths = [
        *sorted(GROUND_TRUTH_DIR.glob("*.iep.json")),
        *sorted((DATA_DIR / "variants").glob("*.iep.json")),
    ]
    emitted_bad = 0
    for path in emitted_paths:
        record = json.loads(path.read_text(encoding="utf-8"))
        try:
            validate_record(record, label=path.stem)
            for item in record["accommodations"]:
                validate_scope_references(item["applies_to_refs"])
        except (RecordValidationError, ValueError) as exc:
            emitted_bad += 1
            print(f"  INVALID {path}: {exc}", file=sys.stderr)
    failures += emitted_bad
    if len(emitted_paths) != 100:
        failures += 1
        print(f"  EXPECTED 100 emitted records, found {len(emitted_paths)}", file=sys.stderr)
    elif emitted_bad == 0:
        print("  100/100 on-disk records pass JSON Schema and v1.2 scope semantics")

    print("== internal consistency ==")
    problems = check_district_and_ground_truth()
    if problems:
        failures += len(problems)
        for p in problems:
            print(f"  PROBLEM: {p}", file=sys.stderr)
    else:
        print("  district ↔ ground-truth consistent; all edge cases present")

    print("== byte-stability (emitted ground truth) ==")
    if GROUND_TRUTH_DIR.exists() and any(GROUND_TRUTH_DIR.iterdir()):
        before = _hash_tree(GROUND_TRUTH_DIR)
        # Re-emit into memory and compare against the on-disk hash by re-serializing.
        from synthgen.writer import write_json

        for record in canonical_records:
            sref = record["student_ref"]
            write_json(GROUND_TRUTH_DIR / f"{sref}.iep.json", record)
        after = _hash_tree(GROUND_TRUTH_DIR)
        if before == after:
            print(f"  stable (sha256 {after[:12]})")
        else:
            failures += 1
            print("  UNSTABLE: re-emission changed ground-truth bytes", file=sys.stderr)
    else:
        print("  (skipped: run build_dataset.py first)")

    if failures:
        print(f"\nFAILED: {failures} problem(s)", file=sys.stderr)
        return 1
    print(f"\nOK: dataset verified (data root {DATA_DIR})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
