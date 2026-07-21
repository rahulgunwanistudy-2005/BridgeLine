"""Builders that turn compact authored content into schema-shaped IEPRecord dicts.

Authored content (accommodation text, goals, edge cases) is specified by hand in
``ground_truth.py``; these helpers fill the repetitive contract fields deterministically
so every record is internally consistent and byte-stable. reconciliation_status is
always None here: these are first extractions in each IEP lineage.
"""

from __future__ import annotations

from typing import Any, Literal, TypedDict

from synthgen.constants import DATASET_EPOCH_ISO, GROUND_TRUTH_MODEL, stable_uuid

# Sentinel for a mandated service that has no provider staffed yet. The schema requires
# a non-empty provider_role, so "no provider" is expressed as this explicit value rather
# than null; the rules engine can detect it as a staffing gap.
UNASSIGNED_PROVIDER = "Unassigned"

Scope = Literal["subject", "context", "all"]


class AccommodationScopeReference(TypedDict):
    scope: Scope
    ref: str
    source_page: int
    source_quote: str
    confidence: float


def scope_reference(
    scope: Scope,
    ref: str,
    *,
    source_page: int,
    source_quote: str,
    confidence: float,
) -> AccommodationScopeReference:
    """Build one source-grounded, document-language applicability reference."""

    return {
        "scope": scope,
        "ref": ref,
        "source_page": source_page,
        "source_quote": source_quote,
        "confidence": confidence,
    }


def _scope_match_key(reference: AccommodationScopeReference) -> tuple[str, str]:
    normalized_ref = " ".join(reference["ref"].split()).casefold()
    return reference["scope"], normalized_ref


def validate_scope_references(references: list[AccommodationScopeReference]) -> None:
    """Enforce v1.2 semantics that are intentionally stronger than the JSON Schema."""

    if not references:
        raise ValueError("applies_to_refs must contain at least one source reference")
    if any(reference["scope"] == "all" for reference in references) and len(references) != 1:
        raise ValueError("an all-scope reference must be the accommodation's only reference")
    match_keys = [_scope_match_key(reference) for reference in references]
    if len(match_keys) != len(set(match_keys)):
        raise ValueError("duplicate normalized (scope, ref) pair in applies_to_refs")


def accommodation(
    student_ref: str,
    key: str,
    *,
    text: str,
    applies_to_refs: list[AccommodationScopeReference],
    source_page: int,
    confidence: float,
) -> dict[str, Any]:
    validate_scope_references(applies_to_refs)
    return {
        "id": stable_uuid("accommodation", student_ref, key),
        "text": text,
        "applies_to_refs": applies_to_refs,
        "source_page": source_page,
        "source_quote": text,
        "confidence": confidence,
        "reconciliation_status": None,
    }


def service_source_quote(
    type: str,
    minutes_per_week: int,
    frequency: str,
    provider_role: str,
) -> str:
    """Return the exact service sentence printed by the deterministic renderer."""

    return (
        f"{type}: {minutes_per_week} minutes per week; {frequency}; "
        f"provider: {provider_role}."
    )


def service(
    student_ref: str,
    key: str,
    *,
    type: str,
    minutes_per_week: int,
    frequency: str,
    provider_role: str,
    start: str | None,
    end: str | None,
    source_page: int,
    confidence: float,
) -> dict[str, Any]:
    return {
        "id": stable_uuid("service", student_ref, key),
        "type": type,
        "minutes_per_week": minutes_per_week,
        "frequency": frequency,
        "provider_role": provider_role,
        "start": start,
        "end": end,
        "source_page": source_page,
        "source_quote": service_source_quote(type, minutes_per_week, frequency, provider_role),
        "confidence": confidence,
        "reconciliation_status": None,
    }


def goal(
    student_ref: str,
    key: str,
    *,
    text: str,
    baseline: str,
    target: str,
    measure: str,
    progress_cadence: str,
    source_page: int,
    confidence: float,
) -> dict[str, Any]:
    return {
        "id": stable_uuid("goal", student_ref, key),
        "text": text,
        "baseline": baseline,
        "target": target,
        "measure": measure,
        "progress_cadence": progress_cadence,
        "source_page": source_page,
        "source_quote": text,
        "confidence": confidence,
        "reconciliation_status": None,
    }


def iep_record(
    *,
    student_ref: str,
    disability_category: str,
    school_year: str,
    accommodations: list[dict[str, Any]],
    services: list[dict[str, Any]],
    goals: list[dict[str, Any]],
    annual_review: str | None,
    triennial_reeval: str | None,
    last_progress_report: str | None,
    field_confidences: dict[str, float],
    page_count: int,
    legibility_scores: list[float],
) -> dict[str, Any]:
    """Assemble a full canonical IEPRecord (schema v1.2, field_confidences embedded)."""

    return {
        "iep_record_id": stable_uuid("iep", student_ref),
        "student_ref": student_ref,
        "disability_category": disability_category,
        "school_year": school_year,
        "accommodations": accommodations,
        "services": services,
        "goals": goals,
        "dates": {
            "annual_review": annual_review,
            "triennial_reeval": triennial_reeval,
            "last_progress_report": last_progress_report,
        },
        "field_confidences": field_confidences,
        "extraction_meta": {
            "model": GROUND_TRUTH_MODEL,
            "run_id": stable_uuid("run", student_ref),
            "page_count": page_count,
            "legibility_scores": legibility_scores,
            "extracted_at": DATASET_EPOCH_ISO,
        },
    }


def field_confidences(
    *,
    student_ref: float,
    disability_category: float,
    school_year: float,
    annual_review: float,
    triennial_reeval: float,
    last_progress_report: float,
) -> dict[str, float]:
    """The six per-field extraction confidences carried inside the canonical record.

    Mirrors the FieldConfidences object in packages/schemas/IEPRecord.json: one 0.0–1.0
    score per canonical scalar/date field. 0.0 signals an absent or unreliable value (a
    field whose date is null must score 0.0). Embedded via ``iep_record(field_confidences=...)``.
    """

    return {
        "student_ref": student_ref,
        "disability_category": disability_category,
        "school_year": school_year,
        "annual_review": annual_review,
        "triennial_reeval": triennial_reeval,
        "last_progress_report": last_progress_report,
    }
