# Task: cc/02c — Source-grounded accommodation scope references (schema v1.2)

## Goal
Regenerate all 12 canonical records, 88 variants, and 100 rendered documents with
truthful `applies_to_refs`, preserving deterministic output and all three scripted
findings—especially RIV-1001 extended time resolving to exactly six enrolled classes.

## Territory
- May edit: `scripts/`, `data/`, `harness/`, `docs/`, `apps/web/`.
- Must not edit: `apps/api/bridgeline/`, `packages/schemas/`, or backend tests.
- Backend/schema gaps discovered during validation will be reported for teammate filing,
  not patched on this branch.

## Source-quote/render synchronization design
- Make the renderer use an explicit four-page form contract: page 1 student/present
  levels, page 2 accommodations, page 3 services, page 4 goals/signatures. This makes
  every authored `source_page` stable and truthful instead of depending on incidental
  text wrapping (the current renderer emits two pages despite authored pages 2–4).
- Store document phrases—not roster codes—in each scope reference. Render the same refs
  into a deterministic `Applicability:` sentence on accommodation page 2: same-scope
  refs are joined as alternatives, while subject and context clauses are joined as an
  intersection. An `all` ref is rendered alone.
- Treat the generated PDF text layer as the authority. Extend dataset verification to
  render every canonical and variant record in memory, extract text per page with
  PyMuPDF, normalize whitespace introduced by line wrapping, and assert every item-level
  `source_quote` and every `applies_to_refs[*].source_quote` is a case-sensitive substring
  of its declared page. A wrong quote or page must fail the build.
- Keep item-level evidence equally truthful: accommodation and goal quotes will be exact
  excerpts of their rendered text; service evidence will match the rendered service
  wording. Variant evidence pages/quotes will be cloned or rebuilt from those same
  canonical phrases rather than invented independently.

## Steps
- [x] Slice 0 — Baseline: run the Riverside acceptance test and current dataset verifier;
      record the expected v1.2 validation failure and confirm no unrelated failures.
- [x] Slice 1 — Contract builders: replace `applies_to` with typed `applies_to_refs` in
      `scripts/synthgen/records.py`; add local semantic checks for non-empty refs,
      exclusive `all`, and unique normalized `(scope, ref)` pairs without touching the
      teammate-owned schema/backend.
- [x] Slice 2 — Canonical records: author varied, truthful refs across all 12 records,
      including genuine `all`, subject-only, context-only, a subject+context intersection,
      and a same-subject-scope union. Encode document phrase `all academic subjects` as
      one low-confidence (`~0.5`) subject ref—not an inferred roster expansion—so extraction
      truthfully routes it through needs-review/unresolved-scope/alias resolution. Use varied
      realistic per-ref confidence values elsewhere.
- [x] Slice 3 — Renderer/evidence: render applicability wording on page 2 in standard PDF,
      two-column PDF, and HTML; enforce the four-page standard PDF layout; add the
      programmatic quote/page verifier and smoke-check all 12 canonical records.
- [x] Slice 4 — Six-class demo gate: resolve RIV-1001 extended-time refs against subject
      display names plus active enrollments, assert exactly six target classes, and assert
      `accommodation_confirmations.csv` still contains exactly the expected 3 confirmed
      and 3 unconfirmed class rows for the same stable accommodation ID.
- [x] Slice 5 — Variants/regeneration: deep-copy/refresh scope refs in `variants.py`,
      regenerate the full dataset (12 + 88 records, 100 documents, 5 hero scans), and
      assert record/document/manifest counts.
- [x] Slice 6 — Quality gates: validate all 100 JSON records against the current
      `packages/schemas/IEPRecord.json`; validate v1.2 scope semantics; verify all rendered
      evidence quotes/pages; confirm the Sharma Goal 2 conflict, extended-time 3-of-6,
      and 20-min/week service findings; run compile/lint/relevant pytest.
- [x] Slice 7 — Reproducibility/self-review: hash the full `data/synthetic` tree, rebuild
      with the fixed seed, compare hashes byte-for-byte, inspect the complete diff, and
      verify `rg` finds no retired `applies_to` key/identifier in `data/` or `scripts/`.

## Risks / open questions
- Teammate follow-up to file: `IEPRecord.json` requires the `applies_to_refs` property but
  its array schema is missing basic, structured-output-compatible `minItems: 1`. Unlike
  conditional `all` exclusivity and normalized duplicate constraints (deliberately kept in
  Pydantic), this belongs in JSON Schema and also signals mandatory evidence to extraction.
  Because schema is teammate territory, this branch will enforce all v1.2 semantics locally
  and report the missing keyword without patching `packages/schemas/`.
- PDF wrapping inserts line breaks into extracted text. Verification will normalize only
  whitespace, not case or wording, so it still proves that quotes are verbatim.
- Forced page boundaries must not overflow into a fifth page for the largest 9-accommodation
  or 5-goal variant. Verification will assert exactly four clean pages for every record.
- Degraded PDFs may intentionally have no reliable text layer. Quote verification will
  run against each record's deterministic clean render before optional raster degradation.

## Done criteria
- [x] All 12 canonical and 88 variant records validate against current IEPRecord JSON Schema.
- [x] Every record passes non-empty/exclusive/unique scope-reference semantic checks.
- [x] Every item and scope-reference quote appears verbatim on its declared clean-PDF page.
- [x] RIV-1001 extended time resolves to six classes and confirmations remain 3 of 6.
- [x] All three scripted findings fire with their expected exact values.
- [x] Exactly 88 variants and 100 manifest documents are regenerated; hero scans remain five.
- [x] Two full fixed-seed builds produce identical `data/synthetic` bytes.
- [x] No retired `applies_to` remains anywhere under `data/` or `scripts/`.
- [x] Python compile, configured lint, relevant pytest, and self-review pass.

## Review
**Shipped:** typed v1.2 scope-reference builders and semantic guards; 46 deliberately
authored canonical accommodations with document-language refs and varied confidence;
RIV-1004 `all academic subjects` preserved as one subject ref at 0.51 confidence; fixed
four-page clean form with student/page continuation headers and applicability wording in
PDF, alternate two-column PDF, and HTML; 88 scope-aware variants; PDF-text evidence and
on-disk semantic verification; six-class roster/confirmation consistency assertions; all
100 records/PDFs and five hero scans regenerated.

**Verified:** 100/100 JSON Schema-valid and scope-semantic-valid; 100/100 clean PDFs exactly
four pages with every item/ref quote present case-sensitively on its declared page; all
three findings fire (40% Goal-2 conflict, extended time 3/6, service −20 min/wk); untouched
Riverside acceptance test passes; remaining backend suite passes 113 tests when the one
uncollectable Hypothesis property-test module is excluded; ruff and py_compile clean;
retired standalone `applies_to` absent from `data/` and `scripts/`; final full-tree rebuild
hash stable at `0d7a5d9d5d9182f180ab19e4abdd1b814a87e607b1aab5db40e789cafb65547f`.
Representative four-page and low-confidence-scope PDFs were rasterized and visually
inspected with no clipping, overlap, or legibility defects.

**Deferred/filed (teammate territory):** `IEPRecord.json` still needs `minItems: 1` on
`applies_to_refs`; recorded in `docs/backend-followups.md`. Full API-suite collection is
also currently blocked before tests run because the existing teammate-owned API venv lacks
its declared dev dependency `hypothesis`; no backend environment or source was modified.

---

# Task: cc/02b — Embed field_confidences into the dataset (schema v1.1)

## Goal
The canonical `packages/schemas/IEPRecord.json` now REQUIRES `field_confidences` as a
top-level, closed object (six required keys). The prior cc/02 work stored these in
sidecar `*.confidences.json` files (correct for the v1 schema at the time, wrong now).
Embed the six confidences directly in every record, delete the sidecar files + code,
regenerate all artifacts, and re-validate against the CURRENT schema — byte-stable, all
3 scripted findings still firing.

## Superseded decision
The "Key decisions" block below (SIDECAR files, records stay pure v1) is OBSOLETE.
Schema v1.1 (restored on this branch in commit 930e998) carries `field_confidences`
inside the record; the backend Pydantic side already requires it there
(`ingest/gate.py`, `ingest/extract.py`, `db/schemas.py`). Embedding is now correct and
backend-aligned — no backend change required.

## How I locate & update the 12 records
The records are NOT hand-edited JSON — they're generated by `scripts/synthgen/ground_truth.py`
(one `_riv_XXXX()` builder each) via `scripts/synthgen/records.py::iep_record()`, then
written by `scripts/build_dataset.py`. The authored confidence values already exist in the
paired `_sc_XXXX()` builders. So I update the *generators*, then regenerate the JSON:
- `records.py::iep_record()` — add a `field_confidences` param; embed it in the record
  dict between `dates` and `extraction_meta` (matches schema property order).
- `records.py::field_confidences()` — return just the six-key confidence dict (drop the
  `iep_record_id`/`student_ref` sidecar wrapper + sidecar docstring).
- `ground_truth.py` — fold each `_sc_XXXX()` value into its `_riv_XXXX()` builder as the
  `field_confidences=` arg; delete `_sc_XXXX`/`_sc_clean`; flatten `_BUILDERS` to record
  builders only; `build_records()` returns `list[dict]`.
- Edge case: RIV-1012 (a clean student, in no finding) → `last_progress_report: null`
  with `field_confidences.last_progress_report = 0.0`.

## What "remove the sidecar" touches
- Generators: `synthgen/records.py`, `synthgen/ground_truth.py`, `synthgen/variants.py`.
- Writers/consumers: `build_dataset.py`, `build_variants.py`, `verify_dataset.py`
  (stop writing/unpacking `*.confidences.json`; iterate records only).
- Seed client (mine): `seed.py` — send the record (now self-describing); drop the
  sidecar read + separate `field_confidences` body param.
- Docs (mine): `docs/seed-api-contract.md` (says field_confidences is optional sidecar
  metadata), `data/synthetic/PROVENANCE.md`/`README.md` if they describe sidecars.
- On-disk: delete `data/synthetic/ground_truth/*.confidences.json` (12) and
  `data/synthetic/variants/*.confidences.json` (88).

## Steps (cc/02b)
- [x] 1. Merge prior cc/02 work onto this branch (merge commit ab53a56, .gitignore resolved).
- [x] 2. Refactor generators to embed field_confidences; delete sidecar code
      (records.py, ground_truth.py, variants.py; consumers build_dataset/build_variants/
      verify_dataset/consistency/progress).
- [x] 3. Update seed.py + contract doc + PROVENANCE/README wording.
- [x] 4. Regenerate: `build_all.py` (12 records, docs, 88 variants, 5 scans).
- [x] 5. Delete stale `*.confidences.json` files from disk (100 removed).
- [x] 6. Validate every generated document vs CURRENT schema (100/100 on-disk .iep.json valid).
- [x] 7. Confirm byte-stability (full-tree double-build hash identical) + all 3 findings fire.

## Done criteria (cc/02b) — ALL MET
- [x] Every record (12 + 88) has an embedded, schema-valid `field_confidences`.
- [x] ≥1 record has `last_progress_report: null` with confidence 0.0 (RIV-1012).
- [x] No `*.confidences.json` files remain; no code reads/writes them.
- [x] `verify_dataset.py` green: 12/12 + 88/88 valid, 3 findings fire, byte-stable.
- [x] Double-build produces byte-identical output (full data/synthetic tree hash identical).

## Review (cc/02b)
**Shipped:** field_confidences embedded in all 100 IEPRecords (schema v1.1); the six
authored confidences per ground-truth record folded from the old `_sc_*` sidecar builders
into each `_riv_*` builder via `iep_record(field_confidences=...)`; RIV-1012 given the
absent-field edge case (last_progress_report null → confidence 0.0). Sidecar concept fully
removed: `field_confidences()` now returns the embedded six-key block, 100 `*.confidences.json`
deleted, and all writers/consumers (build_dataset, build_variants, verify_dataset,
variants._pools, consistency, progress) iterate records-only. seed.py sends the
self-describing record; docs (seed-api-contract, README, PROVENANCE) updated. render.py
two-column path hardened for null dates.
**Verified:** 100/100 on-disk records valid vs current packages/schemas/IEPRecord.json;
3 findings fire (40% conflict, 3/6 gap, −20 min/wk); internal consistency green; full-tree
byte-stable across a clean rebuild; ruff clean. Only RIV-1012's rendered PDF/HTML changed
(field_confidences is not printed on the form; its null date renders "Not stated").
**Backend note (filed, not fixed — teammate territory):** none required. The Pydantic side
already requires field_confidences inside the record (ingest/gate.py, ingest/extract.py,
db/schemas.py), so embedding is backend-aligned.

---

# Task: cc/02 — Synthetic Dataset (Riverside Demo School District)  [PRIOR — reference]

## Goal
Author a fully internally-consistent, obviously-fictional demo dataset — district
structure, 12 hand-authored schema-valid IEPRecords, engineered progress history that
fires 3 scripted findings deterministically, 100 rendered documents (12 + 88 seeded
variants) incl. 5 hero messy scans, an idempotent API seed loader, and PROVENANCE —
such that regeneration from seed is byte-stable and every published harness metric is
credible. Steps 1–2 unblock the teammate's rules engine; push at 2 ping points.

## Key decisions (confirmed with Rahul)
- **field_confidences** → SIDECAR files (`*.confidences.json`), NOT embedded in the
  IEPRecord. Reason: frozen `IEPRecord.json` is v1 with `additionalProperties:false`;
  embedding would fail the schema-validation acceptance gate. Canonical records stay pure v1.
- **Seed loader** → build `seed.py` against a *proposed* API contract, gated so it
  no-ops until the backend endpoints exist. No direct DB writes (territory rule).

## Backend items to FILE with Rahul (teammate territory — I do NOT fix these)
1. `apps/api/bridgeline/ingest/extract.py:13` imports `FieldConfidences` from
   `bridgeline.db.schemas`, which does not define it → `ImportError`; `/ieps/upload`
   cannot import/run on this branch. (Confirmed.)
2. Schema/CHANGELOG drift: commit `f60ddf4` claims to promote `field_confidences` to
   canonical v1.1 but touched no schema file; JSON schema + Pydantic + CHANGELOG all
   still v1. Decide whether v1.1 lands (paired PR) or the field stays draft-only.
3. No seeding endpoints exist for district/roster/calendar/gradebook/service-log/
   progress-signal data, nor for deterministic canonical-IEP injection. `/ieps/upload`
   is upload-only + non-deterministic LLM. Seeding via public API needs new endpoints.
   → I will write the proposed contract in `docs/seed-api-contract.md` for filing.

## Territory
MINE: apps/web/, data/, harness/, docs/, scripts/, deploy config.
NOT MINE: apps/api/bridgeline/, Pydantic side of packages/schemas/ (paired-PR).

### Steps (build order; ★ = ping point)
- [x] **Slice 0 — Scaffold**: dirs, scripts/synthgen/ package, pinned tooling venv, validator.
- [x] **Slice A — STEP 1 (teammate-blocking)**: district + 12 IEPRecords + sidecars.
      12/12 schema-valid; all edge cases present; byte-stable. VERIFIED.
- [x] **Slice B — STEP 2 ★PING 1**: gradebook/service-logs/notes/confirmations; all 3
      findings FIRE (40% conflict, 3/6 gap, −20 min/wk); noise + malformed rows present.
      VERIFIED. → PUSHED at ping 1.
- [x] **Slice C — STEP 3**: scripts/seed.py (stdlib-only, gated, idempotent) +
      docs/seed-api-contract.md + docker-compose seed service (depends_on api healthy).
      Gated no-op + 404-probe verified; compose config valid. DONE.
- [x] **Slice D — STEP 4**: pdf.py (deterministic vector writer) + render.py (IEP form
      PDF+HTML). 12 students rendered; sips/pymupdf confirm valid & form-like; byte-stable.
- [x] **Slice E — STEP 5 ★PING 2**: 5 hero messy scans via ONE parameterized script
      (degrade.py + scans.py + make_messy_scans.py --intensity light/medium/heavy).
      All 5 types present + visually verified; scan1 visibly rough; byte-stable;
      image-only PDFs (no text layer). → PUSHED at ping 2.
- [x] **Slice F — STEP 6**: variants.py + build_variants.py — 88 variant records
      (recombined authored pools), 100 PDFs total (22 degraded), manifest.json. All
      88 schema-valid; byte-stable. build_all.py orchestrates full regeneration.
- [x] **PROVENANCE**: data/synthetic/PROVENANCE.md — generation record + plainly states
      no real student data exists.
- [ ] **PROVENANCE**: data/synthetic/PROVENANCE.md — how generated + "no real student
      data exists in this repo".

### Risks / open questions
- Byte-stability: vector PDFs must have no timestamps/nondeterministic object order;
  raster degradation must pin PIL/numpy + fixed seed + stripped PNG metadata + vendored
  font. Verify by regenerating twice and diffing bytes.
- Internal consistency: student schedule must agree across roster ↔ gradebook ↔
  service log ↔ IEP. Single source of truth (district/*.json) + generators derive from it.
- Font vendoring for raster scans (Step 5) — need a repo-committed open TTF (DejaVu).

### Done criteria
- [ ] All 12 IEPRecords validate against packages/schemas/IEPRecord.json programmatically
- [ ] All 3 scripted findings fire from seeded data (verification script green)
- [ ] Regeneration byte-stable (double-run diff clean)
- [ ] roster ↔ gradebook ↔ service-log ↔ IEP internally consistent (consistency check green)
- [ ] Seeding twice is idempotent (once endpoints exist; gated until then)
- [ ] 5 messy scans span all degradation types; degradation script parameterized
- [ ] PROVENANCE.md present and states no real student data exists

### Review
**Shipped (all 6 steps + PROVENANCE):** deterministic Riverside district + 12 schema-valid
hand-authored IEPRecords (+confidence sidecars); engineered progress firing all 3 findings
with noise; gated idempotent seed.py + proposed API contract + compose wiring; byte-stable
vector-PDF + HTML IEP form renderer (12 students); 5 parameterized hero messy scans (all
degradation types, scan1 visibly rough); 88 seeded variants → 100 documents + manifest;
build_all.py orchestrator.

**Verified:** 12/12 + 88/88 schema-valid; 3 findings fire (asserted); internal consistency
(roster↔gradebook↔service-log↔IEP); full dataset byte-stable across clean rebuilds; lint +
compile clean. Idempotency: seed.py is stateless/upsert-by-design; gated no-op + 404-probe
paths tested (true DB idempotency awaits the backend endpoints).

**Deferred / filed to Rahul (backend territory):** (1) extract.py FieldConfidences ImportError;
(2) schema/CHANGELOG v1.1 drift; (3) missing seed endpoints (spec in docs/seed-api-contract.md).

**Notes:** field_confidences delivered as sidecars (frozen schema forbids embedding);
provider "Unassigned" sentinel; reference date as_of=2026-11-13 baked into calendar.json.
