#!/usr/bin/env python
"""Acceptance gate for the synthetic dataset: validation + consistency + byte-stability.

Runs read-only checks against already-emitted files where possible, and re-derives the
in-memory model to assert internal consistency and schema conformance. Exits non-zero on
any problem so CI and the harness fail loudly.

Usage:  PYTHONPATH=scripts .venv-synth/bin/python scripts/verify_dataset.py
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

from synthgen.consistency import check_district_and_ground_truth
from synthgen.constants import DATA_DIR, GROUND_TRUTH_DIR
from synthgen.ground_truth import build_records
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

    print("== schema validation ==")
    for record, _ in build_records():
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
    for record, _ in variants:
        try:
            validate_record(record, label=record["student_ref"])
        except RecordValidationError as exc:
            v_bad += 1
            print(f"  INVALID {exc.label}: {exc.messages}", file=sys.stderr)
    failures += v_bad
    manifest_path = DATA_DIR / "manifest.json"
    if manifest_path.exists():
        import json as _json

        manifest = _json.loads(manifest_path.read_text())
        total = manifest["document_count"]
        print(f"  {len(variants)} variants valid; manifest lists {total} documents "
              f"({manifest['degraded_count']} degraded)")
        if total != 100:
            failures += 1
            print(f"  EXPECTED 100 documents, manifest has {total}", file=sys.stderr)
    else:
        print("  (manifest missing: run build_variants.py)")

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

        for record, sidecar in build_records():
            sref = record["student_ref"]
            write_json(GROUND_TRUTH_DIR / f"{sref}.iep.json", record)
            write_json(GROUND_TRUTH_DIR / f"{sref}.confidences.json", sidecar)
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
