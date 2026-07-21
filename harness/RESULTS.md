# Validation Harness — Results

> Generated: 2026-07-21 13:41:55 UTC  
> Commit: `23451e3`

## Summary

| Suite | Status | Duration |
|-------|--------|----------|
| Rules (Slice 1) | ✅ PASS (12/12) | 0.13s |
| Acceptance (Slice 3) | ✅ PASS (3/3) | 0.01s |
| Extraction (Slice 2) | ⚠️ SKIPPED | 0.0s |

## Slice 1 — Rules Derivation

Rules engine version: `2026.07.20.5`

Determinism hash: `76cafcd100118f62`

| Student | Obligations | Findings | Deadlines | Deterministic | Status |
|---------|-------------|----------|-----------|---------------|--------|
| RIV-1001 | 49/49 | 15/15 | 3/3 | ✅ | ✅ |
| RIV-1002 | 28/28 | 30/30 | 2/2 | ✅ | ✅ |
| RIV-1003 | 23/23 | 28/28 | 3/3 | ✅ | ✅ |
| RIV-1004 | 21/21 | 18/18 | 3/3 | ✅ | ✅ |
| RIV-1005 | 38/38 | 28/28 | 3/3 | ✅ | ✅ |
| RIV-1006 | 17/17 | 10/10 | 2/2 | ✅ | ✅ |
| RIV-1007 | 28/28 | 29/29 | 2/2 | ✅ | ✅ |
| RIV-1008 | 21/21 | 17/17 | 2/2 | ✅ | ✅ |
| RIV-1009 | 24/24 | 16/16 | 2/2 | ✅ | ✅ |
| RIV-1010 | 18/18 | 17/17 | 3/3 | ✅ | ✅ |
| RIV-1011 | 28/28 | 16/16 | 2/2 | ✅ | ✅ |
| RIV-1012 | 28/28 | 31/31 | 0/0 | ✅ | ✅ |

## Slice 3 — E2E Acceptance

| Finding | Status | Detail |
|---------|--------|--------|
| Sharma Goal 2 conflict | ✅ | Gradebook avg 40% across 8 assessments; teacher note says 'doing well' — conflict confirmed |
| Extended-time 3-of-6 gap | ✅ | Finding fires: Provide 50% extended time on all classroom tests and quizzes. is confirmed in 3 ... M |
| Service −20 min/wk variance | ✅ | 12 weeks short. Sample: Specialized academic instruction is 20 minutes short (variance=-20.0) |

## Slice 2 — Extraction Pipeline

> ⚠️ API server was not available. Results below are a dry-run inventory.

### Clean tier (12 documents)

- Documents: 12 (not processed)

### Degraded tier (88 documents)

- Documents: 88 (not processed)

### Silent-wrong-rate

Not computed (server unavailable)

Estimated cost: **$0.03** USD

---

## Disclosures

- **Rules engine** (Slices 1, 3): fully deterministic, zero LLM calls (AST-enforced boundary). Repeated runs produce byte-identical output.

- **Extraction pipeline** (Slice 2): uses Gemini for OCR and extraction. Results carry residual LLM variance; the silent-wrong-rate is the safety metric.

