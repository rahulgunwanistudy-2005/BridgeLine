"""Builders that turn compact authored content into schema-shaped IEPRecord dicts.

Authored content (accommodation text, goals, edge cases) is specified by hand in
``ground_truth.py``; these helpers fill the repetitive contract fields deterministically
so every record is internally consistent and byte-stable. reconciliation_status is
always None here: these are first extractions in each IEP lineage.
"""

from __future__ import annotations

from typing import Any

from synthgen.constants import DATASET_EPOCH_ISO, GROUND_TRUTH_MODEL, stable_uuid

# Sentinel for a mandated service that has no provider staffed yet. The schema requires
# a non-empty provider_role, so "no provider" is expressed as this explicit value rather
# than null; the rules engine can detect it as a staffing gap.
UNASSIGNED_PROVIDER = "Unassigned"


def accommodation(
    student_ref: str,
    key: str,
    *,
    text: str,
    applies_to: list[str],
    source_page: int,
    source_quote: str,
    confidence: float,
) -> dict[str, Any]:
    return {
        "id": stable_uuid("accommodation", student_ref, key),
        "text": text,
        "applies_to": applies_to,
        "source_page": source_page,
        "source_quote": source_quote,
        "confidence": confidence,
        "reconciliation_status": None,
    }


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
    source_quote: str,
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
        "source_quote": source_quote,
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
    source_quote: str,
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
        "source_quote": source_quote,
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
    page_count: int,
    legibility_scores: list[float],
) -> dict[str, Any]:
    """Assemble a full canonical IEPRecord (frozen v1 schema, no field_confidences)."""

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
    student_ref: str,
    disability_category: float,
    school_year: float,
    annual_review: float,
    triennial_reeval: float,
    last_progress_report: float,
    student_ref_conf: float,
) -> dict[str, Any]:
    """Sidecar object: the six per-field confidences, kept OUT of the canonical record.

    Mirrors the six keys the ingest ExtractionDraft carries. Stored alongside each record
    as ``<student_ref>.confidences.json`` so the canonical IEPRecord stays pure v1 while
    the confidence signal remains available to the confidence gate and harness.
    """

    return {
        "iep_record_id": stable_uuid("iep", student_ref),
        "student_ref": student_ref,
        "field_confidences": {
            "student_ref": student_ref_conf,
            "disability_category": disability_category,
            "school_year": school_year,
            "annual_review": annual_review,
            "triennial_reeval": triennial_reeval,
            "last_progress_report": last_progress_report,
        },
    }
