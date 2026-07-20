#!/usr/bin/env python
"""STEP 6: 88 seeded variant IEPs → 100 documents total, with a manifest.

Builds and validates 88 variant records, renders each to PDF (a deterministic subset
degraded for harness variety), and writes a manifest covering all 100 documents (12 demo
+ 88 variants). Byte-stable given the fixed seed and pinned toolchain.

Usage:  PYTHONPATH=scripts .venv-synth/bin/python scripts/build_variants.py
"""

from __future__ import annotations

import sys

import numpy as np

from synthgen.constants import DATA_DIR, PDF_DIR, RANDOM_SEED
from synthgen.degrade import DegradeParams, print_scan, rasterize_pdf
from synthgen.district import STUDENTS
from synthgen.pdf import build_image_pdf
from synthgen.render import render_pdf
from synthgen.validate import RecordValidationError, validate_record
from synthgen.variants import build_variants
from synthgen.writer import write_bytes, write_json

VARIANTS_DIR = DATA_DIR / "variants"


def _degrade_for(index: int) -> DegradeParams | None:
    """Every fourth variant is a degraded 'scan'; the rest are clean text PDFs."""

    if index % 4 != 0:
        return None
    preset = ("light", "medium", "heavy")[(index // 4) % 3]
    return DegradeParams.preset(preset)


def _render(record: dict, index: int) -> tuple[bytes, bool, str | None]:
    params = _degrade_for(index)
    clean = render_pdf(record)
    if params is None:
        return clean, False, None
    rng = np.random.default_rng(RANDOM_SEED + 5000 + index)
    pages = [print_scan(p, params, rng) for p in rasterize_pdf(clean, params.dpi)]
    intensity = ("light", "medium", "heavy")[(index // 4) % 3]
    return build_image_pdf(pages, jpeg_quality=params.jpeg_quality), True, f"print_scan/{intensity}"


def main() -> int:
    manifest: list[dict] = []

    # 12 demo documents (rendered by render_documents.py).
    for student in STUDENTS:
        ref = student["student_ref"]
        manifest.append({
            "doc_id": ref, "kind": "demo", "student_ref": ref,
            "record_path": f"ground_truth/{ref}.iep.json",
            "pdf_path": f"documents/pdf/{ref}.pdf", "degraded": False, "degradation": None,
        })

    # 88 variants: validate, write record + sidecar, render (subset degraded).
    errors = 0
    for i, (record, sidecar) in enumerate(build_variants(), start=1):
        ref = record["student_ref"]
        try:
            validate_record(record, label=ref)
        except RecordValidationError as exc:
            errors += 1
            print(f"INVALID {ref}: {exc.messages}", file=sys.stderr)
            continue
        write_json(VARIANTS_DIR / f"{ref}.iep.json", record)
        write_json(VARIANTS_DIR / f"{ref}.confidences.json", sidecar)
        pdf_bytes, degraded, degradation = _render(record, i)
        write_bytes(PDF_DIR / f"{ref}.pdf", pdf_bytes)
        manifest.append({
            "doc_id": ref, "kind": "variant", "student_ref": ref,
            "record_path": f"variants/{ref}.iep.json",
            "pdf_path": f"documents/pdf/{ref}.pdf", "degraded": degraded, "degradation": degradation,
        })

    if errors:
        print(f"\nFAILED: {errors} variant record(s) invalid", file=sys.stderr)
        return 1

    from synthgen.scans import SCANS

    hero_scans = [{
        "doc_id": spec.name, "student_ref": spec.student_ref,
        "pdf_path": f"documents/messy/{spec.name}.pdf", "description": spec.description,
    } for spec in SCANS]

    write_json(DATA_DIR / "manifest.json", {
        "document_count": len(manifest),
        "demo_count": sum(1 for m in manifest if m["kind"] == "demo"),
        "variant_count": sum(1 for m in manifest if m["kind"] == "variant"),
        "degraded_count": sum(1 for m in manifest if m["degraded"]),
        "seed": RANDOM_SEED,
        "documents": manifest,
        "hero_scans": hero_scans,
    })
    degraded = sum(1 for m in manifest if m["degraded"])
    print(f"OK: {len(manifest)} documents ({sum(1 for m in manifest if m['kind']=='demo')} demo "
          f"+ {sum(1 for m in manifest if m['kind']=='variant')} variants; {degraded} degraded).")
    print(f"manifest: {DATA_DIR / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
