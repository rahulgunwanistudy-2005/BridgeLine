# Validation Harness

Proves the BridgeLine safety architecture through three evaluation suites.
Every suite reports its own failures — honest numbers, not a marketing chart.

## Quick Start

```bash
# From the repo root:
PYTHONPATH=apps/api:. apps/api/.venv/bin/python3 -m harness rules        # < 1s, $0
PYTHONPATH=apps/api:. apps/api/.venv/bin/python3 -m harness acceptance   # < 1s, $0
PYTHONPATH=apps/api:. apps/api/.venv/bin/python3 -m harness extraction   # ~20min, ~$0.03
PYTHONPATH=apps/api:. apps/api/.venv/bin/python3 -m harness all          # All three
```

Add `-v` for detailed mismatch output. Add `--no-report` to skip RESULTS.md generation.

## Suites

### Slice 1 — Rules (deterministic, free)

Runs `derive_obligations` from the rules engine against all 12 canonical
Riverside Demo records. Compares obligations, findings, and deadlines against
hand-authored expected data under `expected/`. Verifies **byte-identical
determinism** by running derivation twice and comparing serialized output.

- **What it proves:** The AST-enforced deterministic rules engine produces
  the exact expected compliance output for known inputs, with zero variance.
- **CI:** Runs on every PR.

### Slice 2 — Extraction (LLM, costs money)

Uploads 100 documents (12 clean + 88 degraded) to the ingest pipeline via
`POST /ieps/upload`, compares extracted IEPRecords field-by-field against
ground truth, and reports the **silent-wrong-rate** — the headline safety
metric (fields wrong AND confident).

- **What it proves:** The Gemini extraction pipeline doesn't silently
  hallucinate high-confidence wrong answers.
- **Requires:** Running API server (`HARNESS_API_URL`, default `localhost:8000`).
- **CI:** Nightly or `workflow_dispatch` only (LLM cost).
- **Graceful degradation:** If no server, enumerates documents and estimates cost.

### Slice 3 — Acceptance (deterministic, free)

Verifies the three scripted Riverside findings end-to-end:

1. **Sharma Goal 2 conflict** — Gradebook shows ~40% on RIV-1001 comprehension
   assessments while teacher note TN-0001 says "doing well".
2. **Extended-time 3-of-6 gap** — RIV-1001 extended-time accommodation
   confirmed in ENG/MTH/BIO but unconfirmed in HIS/PE/ART.
3. **Service −20 min/wk variance** — RIV-1002 SAI delivered 130 min/wk vs
   150 mandated.

- **What it proves:** Known safety signals produce the exact expected
  findings through the production codepath.
- **CI:** Runs on every PR.

## What CI Runs

| Trigger | Suites | Cost | Duration |
|---------|--------|------|----------|
| PR / push | Rules + Acceptance | $0 | < 1s |
| Nightly / manual | Extraction | ~$0.03 | ~20min |

## Output

Each run generates `harness/RESULTS.md` with:
- Run timestamp, commit hash, rules version
- Per-suite pass/fail summary table
- Per-record obligation/finding/deadline breakdown (rules)
- Per-finding assertion detail (acceptance)
- Per-tier accuracy and silent-wrong-rate (extraction)
- Failure examples with confidence values
- Estimated USD cost
- Variance disclosure

## Environment

The harness imports from `bridgeline.rules` (read-only — no rules engine code
is modified). Set `PYTHONPATH=apps/api:.` to resolve imports, and use the API
venv (`apps/api/.venv/bin/python3`).

| Variable | Default | Description |
|----------|---------|-------------|
| `HARNESS_API_URL` | `http://localhost:8000` | API base URL for extraction |
| `HARNESS_RATE_LIMIT` | `4.0` | Seconds between API calls |

## File Layout

```
harness/
├── __init__.py              # Package with version
├── __main__.py              # CLI: python -m harness {rules|extraction|acceptance|all}
├── config.py                # Paths, constants, reference date
├── loader.py                # Build ApprovedRecord + RosterSnapshot from district data
├── reporter.py              # Auto-generate RESULTS.md
├── generate_expected.py     # One-time script to populate expected/
├── suites/
│   ├── rules.py             # Slice 1: deterministic derivation
│   ├── extraction.py        # Slice 2: LLM pipeline evaluation
│   └── acceptance.py        # Slice 3: scripted E2E findings
├── expected/                # 12 hand-verified expected obligation files
│   ├── RIV-1001.obligations.json
│   └── ...
├── RESULTS.md               # Auto-generated (gitignored in production)
└── README.md                # This file
```
