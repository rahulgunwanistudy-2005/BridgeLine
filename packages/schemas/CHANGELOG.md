# Schema Changelog

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
