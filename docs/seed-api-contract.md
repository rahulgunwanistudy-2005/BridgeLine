# Proposed seed API contract (cc/02 → cx backend)

**Status: PROPOSED — not yet implemented.** `scripts/seed.py` targets this contract and
**no-ops gracefully** (logs and exits 0) until these endpoints exist, so `docker compose up`
never fails on first boot. Filed per the territory rule: the endpoints live in
`apps/api/bridgeline/` (teammate territory); this document is the request.

## Why this is needed

The only public write endpoint today is `POST /ieps/upload`, which runs a **non-deterministic
LLM extraction** over an uploaded file. The synthetic dataset needs to load **deterministic**
ground truth (12 canonical IEPRecords + district structure + progress signals) idempotently,
without an LLM in the loop, and without direct DB writes (territory rule). That requires the
three endpoints below.

## Guardrails (keep seeding off the production surface)

- All three endpoints return **404 unless `SEED_ENABLED=true`** (new setting; default false).
- When enabled, they require header **`X-Seed-Token: <SEED_TOKEN>`** (new setting); mismatch → 403.
- All are **idempotent upserts** keyed by natural identifiers, so running the seed twice
  produces identical state.

## Endpoints

### 1. `POST /admin/seed/district`
Bulk upsert the district graph. Body is `data/synthetic/district/district.json` verbatim.

```
Body: { school, subjects[], teachers[], classes[], students[], enrollments[], calendar }
Upsert keys: school.school_ref, subject.subject_ref, teacher.teacher_ref,
             class.class_ref, student.student_ref, enrollment.(student_ref,class_ref)
Note: classes[].teachers_of_record is a LIST (co-taught classes have two). The current
      `classes.teacher_id` column is single-valued — needs a class_teachers join table,
      or a documented "primary teacher = teachers_of_record[0]" reduction.
Returns: { upserted: { schools, subjects, teachers, classes, students, enrollments } }
```

### 2. `POST /ieps/import`
Deterministically inject one canonical IEPRecord (distinct from `/ieps/upload`, which is
LLM extraction). Idempotent by `record.iep_record_id`; writes/refreshes the current
approved version.

```
Body: { record: <IEPRecord, valid against packages/schemas/IEPRecord.json>,
        approve: true,
        field_confidences?: { student_ref, disability_category, school_year,
                              annual_review, triennial_reeval, last_progress_report } }
Behavior: validate against the IEPRecord Pydantic model; upsert lineage by iep_record_id;
          if approve, mark is_current_approved. field_confidences is optional sidecar
          metadata (the frozen record schema does not carry it).
Returns: { iep_record_id, id, created: bool }
```

### 3. `POST /reconcile/import`
Normalize a progress source into `ProgressSignal`s (already on the API surface in
`03-architecture.md`). Used for gradebook, service logs, and teacher notes.

```
Body: { source_name, signal_type: "grade"|"service_minutes"|"teacher_check_in",
        rows: [ <raw row objects> ] }
Behavior: normalize each row into a ProgressSignal (valid against ProgressSignal.json);
          idempotent by (source.source_name, source.source_record_ref); malformed rows go
          to a quarantine report rather than failing the batch.
Returns: { imported: int, quarantined: [ { source_record_ref, reason } ] }
```

## Idempotency contract

Re-running `seed.py` against an already-seeded database MUST NOT create duplicates or change
state. Every write is an upsert on the natural key above. This is the acceptance gate
"seeding twice produces the same state".

## Until then

`seed.py` probes each endpoint; on `404` it prints a clear "endpoint not yet implemented —
skipping (gated)" line and exits 0. Set `SEED_STRICT=1` to make missing endpoints a hard
failure once the backend lands.
