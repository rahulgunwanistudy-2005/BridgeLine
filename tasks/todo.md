# Task: cc/02 — Synthetic Dataset (Riverside Demo School District)

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
- [ ] **Slice F — STEP 6**: 88 seeded variants (100 docs total), fixed seed, byte-stable.
- [ ] **PROVENANCE**: data/synthetic/PROVENANCE.md.
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
(filled after completion)
