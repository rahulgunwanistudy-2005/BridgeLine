#!/usr/bin/env python
"""Render the 12 demo IEP records to district-form PDFs and HTML (STEP 4).

Deterministic and byte-stable. Reads emitted ground-truth records and writes:
  data/synthetic/documents/pdf/<student_ref>.pdf
  data/synthetic/documents/html/<student_ref>.html

Usage:  PYTHONPATH=scripts .venv-synth/bin/python scripts/render_documents.py
"""

from __future__ import annotations

import json

from synthgen.constants import DOCUMENTS_DIR, GROUND_TRUTH_DIR, PDF_DIR
from synthgen.render import render_html, render_pdf
from synthgen.writer import write_bytes, write_text

HTML_DIR = DOCUMENTS_DIR / "html"


def main() -> int:
    iep_paths = sorted(GROUND_TRUTH_DIR.glob("*.iep.json"))
    if not iep_paths:
        print("no ground-truth records; run build_dataset.py first")
        return 1
    for path in iep_paths:
        record = json.loads(path.read_text(encoding="utf-8"))
        ref = record["student_ref"]
        pdf_bytes = render_pdf(record)
        write_bytes(PDF_DIR / f"{ref}.pdf", pdf_bytes)
        write_text(HTML_DIR / f"{ref}.html", render_html(record))
        print(f"  {ref}: {len(pdf_bytes)} bytes PDF + HTML")
    print(f"OK: rendered {len(iep_paths)} students to {PDF_DIR} and {HTML_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
