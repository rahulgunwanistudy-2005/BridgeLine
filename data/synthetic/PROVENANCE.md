# PROVENANCE — Riverside Demo School District synthetic dataset

## No real student data exists in this repository

**Every record, name, date, document, and score in this dataset is fictional and
machine-generated for demonstration and testing.** There is no real student, teacher,
parent, school, or district data anywhere in this repository, and none was used to
produce it. "Riverside Demo School District" is an invented district; every rendered
document carries a "CONFIDENTIAL — SYNTHETIC DEMO DATA — NOT A REAL STUDENT" banner.

## What this dataset is

A single fictional district for one Fall 2026 semester: 1 school, 6 subjects, 8 teachers,
6 classes (one co-taught), 12 students with IEPs across five disability categories, full
enrollments (one mid-semester), and a semester calendar with holidays. Plus engineered
progress history, 100 rendered IEP documents (12 hand-authored + 88 variants), and 5 hero
messy scans.

## How it was generated

All generation is deterministic Python in `scripts/synthgen/` (isolated from the API in a
dedicated venv; see `scripts/requirements.txt`). Determinism comes from three things, and
nothing reads the wall clock or environment:

- **Stable IDs** — every UUID is `uuid5(fixed_namespace, "kind/key")`, so records renumber
  identically on every run (`synthgen/constants.py`).
- **Fixed epoch** — `extraction_meta.extracted_at` is a pinned constant, never `now()`.
- **One seed** — `RANDOM_SEED = 20260719` drives every random perturbation (variants,
  degradation noise/jitter).

The 12 ground-truth records are **hand-authored** (content designed deliberately in
`synthgen/ground_truth.py`); only the repetitive contract fields are filled programmatically.
The 88 variants **recombine** the authored content pools under the fixed seed.

### Regeneration (byte-stable)

```
python3.11 -m venv .venv-synth && .venv-synth/bin/pip install -r scripts/requirements.txt
PYTHONPATH=scripts .venv-synth/bin/python scripts/build_all.py     # regenerate everything
PYTHONPATH=scripts .venv-synth/bin/python scripts/verify_dataset.py # validate + verify
```

`build_all.py` runs, in order: `build_dataset.py` (district + ground truth + progress) →
`render_documents.py` (12 IEP PDFs + HTML) → `build_variants.py` (88 variants + manifest) →
`make_messy_scans.py` (5 messy scans). Regeneration is **byte-identical** given the pinned
toolchain (jsonschema 4.23.0, Pillow 11.0.0, numpy 2.1.3, pymupdf 1.28.0); the raster/JPEG
steps depend on those exact versions.

## Layout

```
district/     school, subjects, teachers, classes, students, enrollments, calendar (+ split views)
ground_truth/ 12 <ref>.iep.json (schema-valid IEPRecords) + <ref>.confidences.json sidecars
progress/     gradebook/*.csv, service_logs/*.csv, teacher_notes/*.json, accommodation_confirmations.csv
variants/     88 <ref>.iep.json + sidecars (RIV-2001..RIV-2088)
documents/pdf/   100 rendered IEP PDFs (12 demo + 88 variants; 22 variants degraded)
documents/html/  12 demo IEP forms as HTML
documents/messy/ 5 hero messy scans
manifest.json    index of all 100 documents
```

## Key decisions

- **`field_confidences` is a sidecar**, not embedded in the IEPRecord. The frozen
  `packages/schemas/IEPRecord.json` is v1 with `additionalProperties:false`, so embedding
  would fail schema validation. The six per-field confidences live in
  `ground_truth/<ref>.confidences.json` (and per variant), keyed to the same `iep_record_id`.
- **No provider = `"Unassigned"`** — the schema requires a non-empty `provider_role`, so an
  unstaffed service uses this explicit sentinel (RIV-1003).
- **Reference date `as_of = 2026-11-13`** (in `district/calendar.json`) — deadlines evaluate
  against this, not the wall clock, so the demo/harness reproduce on any day.
- **Documents are clean vector PDFs (real text layer); messy scans are image-only** (no text
  layer) — genuinely scan-like for OCR.

## Engineered findings (STEP 2)

Recomputed and asserted by `scripts/verify_dataset.py`:

1. RIV-1001 (A. Sharma) Goal 2 — gradebook ~40% mastery vs a "doing well" teacher note.
2. RIV-1001 extended-time accommodation confirmed in only 3 of 6 classes.
3. RIV-1002 (M. Bell) SAI delivered 130 min/wk against a 150 min/wk mandate (−20 min/wk).

Plus noise: unmappable gradebook/note signals, two malformed CSV rows (quarantine path), and
clean students with no findings.

## Date edge cases (ground truth)

Overdue annual review (RIV-1004, 2026-10-30); triennial due mid-semester (RIV-1003,
2026-11-20); annual review on a holiday (RIV-1005, 2026-11-11 Veterans Day); mid-semester
enrollment (RIV-1006, 2026-10-05); co-taught class (ENG-101, two teachers of record).

## Related

- `README.md` — consumer-facing layout + findings notes.
- `docs/seed-api-contract.md` — the proposed (not-yet-implemented) seed endpoints;
  `scripts/seed.py` targets them and no-ops until they exist.
