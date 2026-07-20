#!/usr/bin/env python
"""Generate the five hero messy scans (STEP 5) — parameterized and deterministic.

The teammate can request harder/easier variants while tuning ingest:
  --intensity {light,medium,heavy}   preset degradation strength (default medium)
  --seed N                           override the fixed random seed
  --scale F                          multiply every effect (overrides preset scale)

Usage:  PYTHONPATH=scripts .venv-synth/bin/python scripts/make_messy_scans.py --intensity heavy
Writes: data/synthetic/documents/messy/<scan>.pdf
"""

from __future__ import annotations

import argparse
import dataclasses

from synthgen.constants import MESSY_DIR, RANDOM_SEED
from synthgen.degrade import DegradeParams
from synthgen.scans import build_all_scans
from synthgen.writer import write_bytes


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the five hero messy scans.")
    parser.add_argument("--intensity", choices=["light", "medium", "heavy"], default="medium")
    parser.add_argument("--seed", type=int, default=RANDOM_SEED)
    parser.add_argument("--scale", type=float, default=None,
                        help="override the preset effect scale")
    args = parser.parse_args()

    params = DegradeParams.preset(args.intensity)
    if args.scale is not None:
        params = dataclasses.replace(params, scale=args.scale)

    print(f"== STEP 5: messy scans (intensity={args.intensity}, seed={args.seed}, "
          f"scale={params.scale}) ==")
    for spec, pdf_bytes in build_all_scans(params, seed=args.seed):
        out = MESSY_DIR / f"{spec.name}.pdf"
        write_bytes(out, pdf_bytes)
        print(f"  {spec.name}: {len(pdf_bytes):>7} bytes  [{spec.student_ref}] {spec.description}")
    print(f"OK: 5 messy scans written to {MESSY_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
