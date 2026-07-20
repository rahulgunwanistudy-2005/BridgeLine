#!/usr/bin/env python
"""Emit and validate the Riverside district structure and 12 ground-truth IEPRecords.

Thin CLI: wire modules, write deterministic JSON, validate every record against the
frozen schema. Fails loudly (non-zero exit) if any record violates the contract.

Usage:  PYTHONPATH=scripts .venv-synth/bin/python scripts/build_dataset.py
"""

from __future__ import annotations

import sys

from synthgen.constants import (
    DISTRICT_DIR,
    GRADEBOOK_DIR,
    GROUND_TRUTH_DIR,
    PROGRESS_DIR,
    SERVICE_LOG_DIR,
    TEACHER_NOTES_DIR,
)
from synthgen.district import build_district
from synthgen.ground_truth import build_records
from synthgen.progress import (
    CONFIRMATION_COLUMNS,
    GRADEBOOK_COLUMNS,
    SERVICE_LOG_COLUMNS,
    build_confirmations,
    build_gradebook,
    build_service_logs,
    build_teacher_notes,
)
from synthgen.validate import RecordValidationError, validate_record
from synthgen.writer import write_csv, write_json


def emit_district() -> None:
    district = build_district()
    write_json(DISTRICT_DIR / "district.json", district)
    # Also split the high-traffic collections into their own files for the seed loader.
    for key in ("school", "subjects", "teachers", "classes", "students", "enrollments", "calendar"):
        write_json(DISTRICT_DIR / f"{key}.json", district[key])
    counts = {k: len(district[k]) for k in ("subjects", "teachers", "classes", "students", "enrollments")}
    print(f"district: {counts}; instructional_days={district['calendar']['instructional_day_count']}")


def emit_and_validate_records() -> int:
    errors = 0
    for record in build_records():
        sref = record["student_ref"]
        try:
            validate_record(record, label=sref)
        except RecordValidationError as exc:
            errors += 1
            print(f"INVALID {sref}:", file=sys.stderr)
            for message in exc.messages:
                print(f"  - {message}", file=sys.stderr)
            continue
        write_json(GROUND_TRUTH_DIR / f"{sref}.iep.json", record)
        print(
            f"  {sref}: {len(record['accommodations'])} accommodations, "
            f"{len(record['services'])} services, {len(record['goals'])} goals — valid"
        )
    return errors


def emit_progress() -> None:
    gradebook, malformed = build_gradebook()
    for class_ref, rows in gradebook.items():
        raw = [line for cref, line in malformed if cref == class_ref]
        write_csv(GRADEBOOK_DIR / f"{class_ref}.csv", GRADEBOOK_COLUMNS, rows, raw or None)
    total_rows = sum(len(r) for r in gradebook.values())
    print(f"  gradebook: {len(gradebook)} classes, {total_rows} rows, {len(malformed)} malformed")

    logs = build_service_logs()
    for student_ref, rows in logs.items():
        write_csv(SERVICE_LOG_DIR / f"{student_ref}.csv", SERVICE_LOG_COLUMNS, rows)
    print(f"  service logs: {len(logs)} students, {sum(len(r) for r in logs.values())} sessions")

    notes = build_teacher_notes()
    write_json(TEACHER_NOTES_DIR / "teacher_notes.json", notes)
    print(f"  teacher notes: {len(notes)}")

    confirmations = build_confirmations()
    write_csv(PROGRESS_DIR / "accommodation_confirmations.csv",
              CONFIRMATION_COLUMNS, confirmations)
    print(f"  confirmations: {len(confirmations)} rows")


def main() -> int:
    print("== STEP 1: district ==")
    emit_district()
    print("== STEP 1: ground-truth IEPRecords ==")
    errors = emit_and_validate_records()
    if errors:
        print(f"\nFAILED: {errors} record(s) invalid against packages/schemas/IEPRecord.json",
              file=sys.stderr)
        return 1
    print("== STEP 2: progress history (gradebook / service logs / notes / confirmations) ==")
    emit_progress()
    print("\nOK: 12/12 records valid; district, ground truth, and progress emitted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
