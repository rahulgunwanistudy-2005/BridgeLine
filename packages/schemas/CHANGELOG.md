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

## v1.2 — 2026-07-20 — IMPLEMENTED, PENDING PAIRED APPROVAL

Generalize `ObligationSet` from teacher/class-only grouping to typed assignee and
context fields. Replace mandatory `accommodation_id` provenance with
`source_kind` + `source_ref`, allowing teacher-access and provider obligations to
trace truthfully to an approved IEP version or service without inventing an
accommodation source. Frontend regeneration and paired human approval are merge
gates.

Replace `Accommodation.applies_to` with required, self-describing
`Accommodation.applies_to_refs`. Each scope reference preserves its document
phrase, source page, source quote, and confidence. References within one scope
are alternatives; subject and context scopes combine by intersection. The
`all` scope is exclusive and means genuinely unconstrained applicability, such
as “across all classes”; qualified phrases such as “all academic subjects” are
never collapsed to `all`.

Add `Obligation.scope_provenance` so each accommodation-derived obligation
identifies the exact approved scope references that caused its assignee/context
fan-out. Services intentionally have no applicability references: their
obligations resolve through `provider_role` and service assignments rather than
classroom scope.

Add `compliance_admin` to `AuditEvent.actor.actor_role` for district-wide scope
alias creation and revocation. Case managers may resolve only a specific
approved IEP scope finding; reusable district mappings require the separate
compliance-administrator role. Both actions are append-only audited.
