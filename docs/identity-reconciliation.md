# IEP identity reconciliation — cx/01 scope

Identity reconciliation is part of the cx/01 ingest pipeline. It must be implemented
before the extraction pipeline can persist re-extracted IEP records.

## Ownership and location

- Pure matching and ID carry-forward logic belongs in
  `apps/api/bridgeline/ingest/identity.py`.
- Pipeline orchestration fetches the prior **approved** `IEPRecord` for the same
  `iep_record_id` and passes it to the identity reconciler. The pure matcher does
  not open database sessions itself.
- Reconciliation runs after structured extraction validation and before confidence
  gating, human approval, obligation derivation, or persistence.
- The reconciler is deterministic and must not import or call the LLM gateway.

## Required behavior

1. If no prior approved record exists, keep the lineage's system-assigned stable
   `iep_record_id`, assign stable UUIDs to extracted accommodations, services, and
   goals, and set every `reconciliation_status` to `null`.
2. For a later extraction, compare each extracted item with the corresponding items
   in the prior approved record using normalized exact content and source anchors.
3. A unique prior match carries the prior UUID forward and sets status to `matched`.
4. An item with no credible prior match receives a new UUID and status `new`.
5. Multiple credible prior matches retain a provisional UUID, set status to
   `ambiguous`, and force a `needs_review` pipeline event. Human resolution either
   carries forward the selected prior UUID or confirms the item as new.
6. Extraction `confidence` is never used as reconciliation status. Confidence
   answers whether text was read correctly; reconciliation answers whether identity
   was preserved across versions.

This contract gives cx/04 version-diff logic stable item identities without allowing
an uncertain match to silently inherit a legal obligation's history.
