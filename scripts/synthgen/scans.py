"""The five hero messy-scan recipes, composed from clean renders + degradations.

Each recipe is deterministic given the base seed and DegradeParams. The five cover every
degradation type in the spec; scan 1 is intentionally the visibly-rough, on-camera one.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable

import numpy as np

from synthgen.constants import GROUND_TRUTH_DIR, RANDOM_SEED
from synthgen.degrade import (
    DegradeParams,
    add_handwriting,
    add_stamp_and_signature,
    print_scan,
    rasterize_pdf,
    rotate,
)
from synthgen.pdf import build_image_pdf
from synthgen.render import render_pdf, render_two_column_pdf


@dataclass(frozen=True)
class ScanSpec:
    name: str
    student_ref: str
    description: str
    recipe: Callable[[dict, DegradeParams, np.random.Generator], bytes]


def _load_record(student_ref: str) -> dict:
    return json.loads((GROUND_TRUTH_DIR / f"{student_ref}.iep.json").read_text(encoding="utf-8"))


def _scan_1_print(record, params, rng):
    """Print-and-scan: rotation ±3°, gaussian noise, contrast drift (visibly rough)."""

    pages = rasterize_pdf(render_pdf(record), params.dpi)
    out = [print_scan(p, params, rng) for p in pages]
    return build_image_pdf(out, jpeg_quality=params.jpeg_quality)


def _scan_2_handwriting(record, params, rng):
    """Handwritten margin annotations + a crossed-out line over a light scan."""

    pages = rasterize_pdf(render_pdf(record), params.dpi)
    light = DegradeParams(scale=0.5, rotation_deg=1.0, noise_sigma=6.0,
                          contrast_factor=0.92, jpeg_quality=params.jpeg_quality)
    out = []
    for i, p in enumerate(pages):
        p = print_scan(p, light, rng, deg=0.8)
        p = p.convert("RGB")
        if i == 0:
            p = add_handwriting(p, rng)
        out.append(p)
    return build_image_pdf(out, jpeg_quality=params.jpeg_quality)


def _scan_3_stamp(record, params, rng):
    """A district stamp and a signature overlapping printed text (kept in color)."""

    pages = rasterize_pdf(render_pdf(record), params.dpi)
    out = []
    for i, p in enumerate(pages):
        p = p.convert("RGB")
        if i == 0:
            p = add_stamp_and_signature(p, rng)
        out.append(p)
    return build_image_pdf(out, jpeg_quality=max(params.jpeg_quality, 82))


def _scan_4_upside_down(record, params, rng):
    """One page upside down within an otherwise clean document."""

    pages = rasterize_pdf(render_pdf(record), params.dpi)
    light = DegradeParams(scale=0.4, rotation_deg=0.6, noise_sigma=4.0,
                          contrast_factor=0.95, jpeg_quality=params.jpeg_quality)
    flip_index = len(pages) - 1  # flip the last page
    out = []
    for i, p in enumerate(pages):
        p = print_scan(p, light, rng, deg=0.4)
        if i == flip_index:
            p = rotate(p, 180)
        out.append(p)
    return build_image_pdf(out, jpeg_quality=params.jpeg_quality)


def _scan_5_two_column_mixed(record, params, rng):
    """Two-column layout variant with mixed clean and scanned pages."""

    clean_pages = rasterize_pdf(render_pdf(record), params.dpi)
    tc_pages = rasterize_pdf(render_two_column_pdf(record), params.dpi)
    # Page 1: clean (undegraded raster). Page 2: scanned two-column variant.
    out = [clean_pages[0].convert("L")]
    for p in tc_pages:
        out.append(print_scan(p, params, rng, deg=1.4))
    return build_image_pdf(out, jpeg_quality=params.jpeg_quality)


SCANS: list[ScanSpec] = [
    ScanSpec("scan1-print-scan", "RIV-1001",
             "Print-and-scan: rotation +/-3 deg, gaussian noise, contrast drift", _scan_1_print),
    ScanSpec("scan2-handwriting", "RIV-1004",
             "Handwritten margin annotations and a crossed-out line", _scan_2_handwriting),
    ScanSpec("scan3-stamp-signature", "RIV-1005",
             "District stamp and signature overlapping printed text", _scan_3_stamp),
    ScanSpec("scan4-upside-down", "RIV-1002",
             "One page upside down within an otherwise clean document", _scan_4_upside_down),
    ScanSpec("scan5-two-column-mixed", "RIV-1010",
             "Two-column layout variant with mixed clean/scanned pages", _scan_5_two_column_mixed),
]


def build_all_scans(params: DegradeParams, seed: int = RANDOM_SEED) -> list[tuple[ScanSpec, bytes]]:
    results: list[tuple[ScanSpec, bytes]] = []
    for index, spec in enumerate(SCANS):
        rng = np.random.default_rng(seed + index * 101)
        record = _load_record(spec.student_ref)
        results.append((spec, spec.recipe(record, params, rng)))
    return results
