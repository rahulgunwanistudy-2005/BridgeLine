#!/usr/bin/env python
"""Regenerate the entire synthetic dataset, in dependency order, deterministically.

Runs each stage's main() in-process so a single command reproduces every artifact:
  1. build_dataset    district + 12 ground-truth records + progress history
  2. render_documents 12 demo IEP PDFs + HTML
  3. build_variants   88 variant records + PDFs + 100-doc manifest
  4. make_messy_scans 5 hero messy scans (medium intensity)

Usage:  PYTHONPATH=scripts .venv-synth/bin/python scripts/build_all.py
"""

from __future__ import annotations

import sys

import build_dataset
import build_variants
import make_messy_scans
import render_documents


def main() -> int:
    stages = [
        ("build_dataset", lambda: build_dataset.main()),
        ("render_documents", lambda: render_documents.main()),
        ("build_variants", lambda: build_variants.main()),
        ("make_messy_scans", lambda: make_messy_scans.main()),
    ]
    for name, run in stages:
        print(f"\n########## {name} ##########")
        code = run()
        if code != 0:
            print(f"stage {name} failed with exit code {code}", file=sys.stderr)
            return code
    print("\nAll stages complete. Run scripts/verify_dataset.py to validate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
