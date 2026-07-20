"""Acceptance checks against the committed Riverside synthetic district data."""

import csv
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

from bridgeline.db.schemas import IEPRecord
from bridgeline.rules.families.distribution import TeacherAccommodationsRule
from bridgeline.rules.types import (
    AccommodationClassState,
    ApprovedRecord,
    RosterSnapshot,
    RuleState,
)

DATA_ROOT = Path(__file__).resolve().parents[4] / "data" / "synthetic"


def test_riverside_1001_extended_time_is_confirmed_in_three_of_six_classes(
    approved_record: ApprovedRecord, roster: RosterSnapshot
) -> None:
    source_record = IEPRecord.model_validate_json(
        (DATA_ROOT / "ground_truth" / "RIV-1001.iep.json").read_text(encoding="utf-8")
    )
    accommodation_id = UUID("3b341238-caab-51d4-8b11-a3913e1fa7d7")
    source_accommodation = next(
        item for item in source_record.accommodations if item.id == accommodation_id
    )
    accommodation = source_accommodation
    with (DATA_ROOT / "progress" / "accommodation_confirmations.csv").open(
        encoding="utf-8", newline=""
    ) as source:
        rows = tuple(
            row
            for row in csv.DictReader(source)
            if row["student_ref"] == "RIV-1001" and row["accommodation_id"] == str(accommodation_id)
        )
    class_states = tuple(
        AccommodationClassState(
            accommodation_id=accommodation_id,
            class_ref=_required(row, "class_ref"),
            obligation_refs=(uuid5(NAMESPACE_URL, _required(row, "row_id")),),
            confirmed=_required(row, "confirmed") == "true",
        )
        for row in rows
    )
    approved = approved_record.model_copy(
        update={
            "student_id": uuid5(NAMESPACE_URL, source_record.student_ref),
            "record": source_record,
        }
    )
    state = RuleState(
        approved=approved,
        roster=roster.model_copy(update={"accommodation_classes": class_states}),
    )

    finding = TeacherAccommodationsRule().check(state)[0]

    expected = f"{accommodation.text} is confirmed in 3 of 6 classes; 3 classes remain unconfirmed."
    assert len(rows) == 6
    assert {item.class_ref for item in class_states if item.confirmed} == {
        "ENG-101",
        "MTH-101",
        "BIO-101",
    }
    assert {item.class_ref for item in class_states if not item.confirmed} == {
        "HIS-101",
        "PE-101",
        "ART-101",
    }
    assert finding.title == expected
    assert finding.detail == expected
    assert finding.measurements == {
        "confirmed_classes": 3,
        "total_classes": 6,
        "unconfirmed_classes": 3,
    }


def _required(row: dict[str, str | None], key: str) -> str:
    value = row.get(key)
    if value is None or not value:
        raise AssertionError(f"Riverside confirmation row is missing {key}")
    return value
