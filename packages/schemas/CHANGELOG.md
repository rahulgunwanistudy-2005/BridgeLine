# Schema Changelog

## v1.1 — 2026-07-19 — IMPLEMENTED, PENDING PAIRED APPROVAL

Added the required `IEPRecord.field_confidences` object for the six canonical
scalar and date fields: `student_ref`, `disability_category`, `school_year`,
`annual_review`, `triennial_reeval`, and `last_progress_report`. Every value is
bounded from 0.0 to 1.0, and 0.0 is required when the corresponding value is
absent or unreliable. This closes the silent-confidence gap for fields that do
not carry item-level confidence.

## v1 — 2026-07-19 — IMPLEMENTED, PENDING PAIRED APPROVAL

Initial contract: IEPRecord, ObligationSet, TeacherBrief, ProgressSignal,
AuditEvent, PipelineStatusEvent. `IEPRecord.iep_record_id` identifies a stable
physical-IEP lineage; accommodation, service, and goal IDs are carried forward
across re-extractions by explicit identity reconciliation. Each extracted item
records that separate identity decision as `matched`, `new`, `ambiguous`, or
first-extraction `null`; cx/01 implementation ownership is documented in
`docs/identity-reconciliation.md`.

Approved field list: Rahul. Final paired approval: pending.

Changes from here require a paired PR: Codex updates Pydantic, Claude Code
regenerates TS types, both humans approve. Log every change below with the reason.
