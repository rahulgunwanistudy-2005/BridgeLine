"""88 seeded variant IEPRecords (→100 documents total) for the validation harness.

Variants deterministically recombine the authored content pools from the 12 ground-truth
records into fresh, schema-valid records with new stable IDs — realistic synthetic IEPs
without hand-authoring 88 more. A fixed seed makes generation byte-stable, so harness
numbers are reproducible. All names are obviously fictional; no real student data.
"""

from __future__ import annotations

import random
from typing import Any

from synthgen.constants import RANDOM_SEED, SCHOOL_YEAR
from synthgen.ground_truth import build_records
from synthgen.records import (
    UNASSIGNED_PROVIDER,
    accommodation,
    field_confidences,
    goal,
    iep_record,
    service,
)

VARIANT_COUNT = 88

_CATEGORIES = [
    "Specific learning disability",
    "Autism",
    "Other health impairment (ADHD)",
    "Speech or language impairment",
    "Hearing impairment",
]

_FIRST = ["Ava", "Liam", "Mia", "Kai", "Zoe", "Omar", "Nina", "Leo", "Ivy", "Tariq",
          "Rosa", "Finn", "Amara", "Cole", "Sana", "Reid", "Lena", "Jose", "Maya", "Dev",
          "Iris", "Beau"]
_LAST = ["Okoro", "Vance", "Petrov", "Adeyemi", "Sato", "Molina", "Frost", "Ibrahim",
         "Novak", "Reyes", "Haddad", "Quinn", "Osei", "Park", "Sole", "Berg", "Cruz",
         "Nair", "Wolfe", "Diaz", "Roy", "Kade"]


def _pools() -> dict[str, list[dict[str, Any]]]:
    """Collect accommodation / service / goal content from the 12 base records."""

    acc: list[dict[str, Any]] = []
    svc: list[dict[str, Any]] = []
    gol: list[dict[str, Any]] = []
    for record in build_records():
        acc.extend(record["accommodations"])
        svc.extend(record["services"])
        gol.extend(record["goals"])
    return {"acc": acc, "svc": svc, "gol": gol}


def _variant_ref(i: int) -> str:
    return f"RIV-2{i:03d}"


def _display_name(i: int) -> str:
    return f"{_FIRST[i % len(_FIRST)]} {_LAST[(i * 7) % len(_LAST)]}"


def _pick(rng: random.Random, pool: list[dict[str, Any]], k: int) -> list[dict[str, Any]]:
    k = min(k, len(pool))
    return rng.sample(pool, k)


def _dates(rng: random.Random) -> tuple[str, str, str]:
    # ~1 in 6 variants carries an overdue annual review; the rest are upcoming.
    if rng.random() < 0.17:
        annual = rng.choice(["2026-10-12", "2026-10-27", "2026-11-03", "2026-09-30"])
    else:
        annual = rng.choice(["2027-01-14", "2027-02-11", "2027-03-09", "2027-04-22", "2027-05-19"])
    triennial = rng.choice(["2028-09-15", "2028-12-04", "2029-01-22", "2029-03-30", "2026-11-18"])
    last_progress = rng.choice(["2026-09-25", "2026-10-09", "2026-10-16", "2026-10-30"])
    return annual, triennial, last_progress


def _build_one(i: int, pools: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    ref = _variant_ref(i)
    rng = random.Random(f"{RANDOM_SEED}:variant:{i}")

    n_acc = rng.randint(3, 9)
    n_svc = rng.randint(1, 3)
    n_gol = rng.randint(2, 5)

    accommodations = []
    for j, src in enumerate(_pick(rng, pools["acc"], n_acc)):
        references = [
            {
                **reference,
                "source_page": 2,
                "confidence": (
                    reference["confidence"]
                    if reference["ref"] == "all academic subjects"
                    else round(rng.uniform(0.76, 0.96), 2)
                ),
            }
            for reference in src["applies_to_refs"]
        ]
        accommodations.append(accommodation(
            ref, f"a{j}", text=src["text"], applies_to_refs=references,
            source_page=2,
            confidence=round(rng.uniform(0.78, 0.97), 2)))

    services = []
    for j, src in enumerate(_pick(rng, pools["svc"], n_svc)):
        provider = UNASSIGNED_PROVIDER if (i % 13 == 0 and j == 0) else src["provider_role"]
        services.append(service(
            ref, f"svc{j}", type=src["type"], minutes_per_week=src["minutes_per_week"],
            frequency=src["frequency"], provider_role=provider,
            start="2026-08-17", end="2027-05-28", source_page=3,
            confidence=round(rng.uniform(0.78, 0.95), 2)))

    goals = []
    for j, src in enumerate(_pick(rng, pools["gol"], n_gol)):
        goals.append(goal(
            ref, f"g{j}", text=src["text"], baseline=src["baseline"], target=src["target"],
            measure=src["measure"], progress_cadence=src["progress_cadence"],
            source_page=4,
            confidence=round(rng.uniform(0.78, 0.96), 2)))

    annual, triennial, last_progress = _dates(rng)
    confidences = field_confidences(
        student_ref=0.99,
        disability_category=round(rng.uniform(0.9, 0.98), 2), school_year=0.99,
        annual_review=round(rng.uniform(0.85, 0.96), 2),
        triennial_reeval=round(rng.uniform(0.82, 0.94), 2),
        last_progress_report=round(rng.uniform(0.85, 0.95), 2))
    return iep_record(
        student_ref=ref, disability_category=_CATEGORIES[i % len(_CATEGORIES)],
        school_year=SCHOOL_YEAR, accommodations=accommodations, services=services, goals=goals,
        annual_review=annual, triennial_reeval=triennial, last_progress_report=last_progress,
        field_confidences=confidences,
        page_count=4, legibility_scores=[1.0, 0.98, 0.97, 0.98])


def build_variants() -> list[dict[str, Any]]:
    """Return the 88 variant IEPRecords (field_confidences embedded), deterministically."""

    pools = _pools()
    return [_build_one(i, pools) for i in range(1, VARIANT_COUNT + 1)]
