"""Contract tests for JSON Schema and generated Pydantic model round trips."""

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

from bridgeline.db.schemas import (
    Accommodation,
    AuditEvent,
    FieldConfidences,
    Goal,
    IEPRecord,
    Measurement,
    ObligationSet,
    PipelineStatusEvent,
    ProgressSignal,
    Service,
    TeacherBrief,
)

REPOSITORY_SCHEMA_DIRECTORY = Path(__file__).resolve().parents[3] / "packages" / "schemas"
CONTAINER_SCHEMA_DIRECTORY = Path(__file__).resolve().parents[1] / "packages" / "schemas"
SCHEMA_DIRECTORY = (
    REPOSITORY_SCHEMA_DIRECTORY
    if REPOSITORY_SCHEMA_DIRECTORY.is_dir()
    else CONTAINER_SCHEMA_DIRECTORY
)

SAMPLES: dict[str, dict[str, Any]] = {
    "IEPRecord": {
        "iep_record_id": "11111111-1111-4111-8111-111111111111",
        "student_ref": "student-rivera",
        "disability_category": "Specific learning disability",
        "school_year": "2026-2027",
        "accommodations": [
            {
                "id": "11111111-1111-4111-8111-111111111112",
                "text": "Provide 50 percent extended time on classroom assessments.",
                "applies_to_refs": [
                    {
                        "scope": "all",
                        "ref": "across all classes",
                        "source_page": 7,
                        "source_quote": "50% extended time across all classes",
                        "confidence": 0.98,
                    }
                ],
                "source_page": 7,
                "source_quote": "50% extended time on classroom assessments",
                "confidence": 0.98,
                "reconciliation_status": "matched",
            }
        ],
        "services": [
            {
                "id": "11111111-1111-4111-8111-111111111113",
                "type": "Specialized academic instruction",
                "minutes_per_week": 150,
                "frequency": "30 minutes, five times weekly",
                "provider_role": "Special education teacher",
                "start": "2026-08-17",
                "end": "2027-05-28",
                "source_page": 12,
                "source_quote": "Specialized academic instruction 30 minutes 5x weekly",
                "confidence": 0.96,
                "reconciliation_status": "new",
            }
        ],
        "goals": [
            {
                "id": "11111111-1111-4111-8111-111111111114",
                "text": "Given a grade-level passage, identify the main idea with 80% accuracy.",
                "baseline": "Identifies the main idea with 45% accuracy.",
                "target": "80% accuracy across three consecutive probes.",
                "measure": "Curriculum-based reading probe",
                "progress_cadence": "Every two weeks",
                "source_page": 9,
                "source_quote": "identify the main idea with 80% accuracy",
                "confidence": 0.94,
                "reconciliation_status": "ambiguous",
            }
        ],
        "dates": {
            "annual_review": "2027-05-10",
            "triennial_reeval": "2029-04-22",
            "last_progress_report": None,
        },
        "field_confidences": {
            "student_ref": 0.99,
            "disability_category": 0.97,
            "school_year": 0.99,
            "annual_review": 0.98,
            "triennial_reeval": 0.96,
            "last_progress_report": 0.0,
        },
        "extraction_meta": {
            "model": "gpt-5.6",
            "run_id": "11111111-1111-4111-8111-111111111115",
            "page_count": 2,
            "legibility_scores": [0.99, 0.87],
            "extracted_at": "2026-07-19T03:00:00Z",
        },
    },
    "ObligationSet": {
        "assignee_kind": "teacher",
        "assignee_ref": "teacher-nguyen",
        "assignee_role": "teacher-of-record",
        "context_kind": "class",
        "context_ref": "class-ela-03",
        "subject": "English language arts",
        "generated_at": "2026-07-19T03:01:00Z",
        "rules_version": "2026.07.1",
        "obligations": [
            {
                "id": "22222222-2222-4222-8222-222222222221",
                "student_ref": "student-rivera",
                "source_kind": "accommodation",
                "source_ref": "11111111-1111-4111-8111-111111111112",
                "scope_provenance": [
                    {
                        "scope": "all",
                        "ref": "across all classes",
                        "source_page": 7,
                        "source_quote": "50% extended time across all classes",
                        "confidence": 0.98,
                    }
                ],
                "rule_id": "teacher-informed-accommodations",
                "citation": "34 CFR §300.323(d)(2)(ii)",
                "action_text": "Provide 50 percent extended time on classroom assessments.",
                "practice_text": None,
                "status": "pending",
                "confirmed_at": None,
                "flag_reason": None,
            }
        ],
    },
    "TeacherBrief": {
        "brief_id": "33333333-3333-4333-8333-333333333331",
        "teacher_ref": "teacher-nguyen",
        "class_ref": "class-ela-03",
        "subject": "English language arts",
        "school_year": "2026-2027",
        "generated_at": "2026-07-19T03:02:00Z",
        "rules_version": "2026.07.1",
        "status": "draft",
        "released_at": None,
        "confirmed_at": None,
        "flag_reason": None,
        "responsibility": {
            "text": "Provide each listed accommodation as written in this class.",
            "citation": "34 CFR §300.323(d)",
        },
        "students": [
            {
                "student_ref": "student-rivera",
                "student_name": "Maya Rivera",
                "obligations": [
                    {
                        "obligation_id": "22222222-2222-4222-8222-222222222221",
                        "accommodation_id": "11111111-1111-4111-8111-111111111112",
                        "accommodation_text": (
                            "Provide 50 percent extended time on classroom assessments."
                        ),
                        "action_text": (
                            "Provide 50 percent extended time on classroom assessments."
                        ),
                        "practice_text": (
                            "Set a 45-minute window when the class receives 30 minutes."
                        ),
                        "source_page": 7,
                        "source_quote": "50% extended time on classroom assessments",
                        "source_confidence": 0.98,
                        "rule_id": "distribution.all-classes",
                        "citation": "34 CFR §300.323(d)",
                    }
                ],
            }
        ],
    },
    "ProgressSignal": {
        "signal_id": "44444444-4444-4444-8444-444444444441",
        "student_ref": "student-rivera",
        "signal_type": "grade",
        "observed_at": "2026-07-18T14:00:00Z",
        "ingested_at": "2026-07-19T03:03:00Z",
        "recorded_by": {"actor_ref": "teacher-nguyen", "actor_role": "teacher"},
        "measurement": {
            "metric": "main_idea_accuracy",
            "numeric_value": 72.0,
            "text_value": None,
            "unit": "percent",
        },
        "source": {
            "source_name": "gradebook-july.csv",
            "source_record_ref": "row-18",
            "source_excerpt": "student-rivera,main_idea_accuracy,72,percent",
        },
        "goal_mapping": {
            "goal_id": "11111111-1111-4111-8111-111111111114",
            "status": "confirmed",
            "confidence": 0.99,
            "rationale": "The imported metric directly matches the goal measure.",
        },
    },
    "AuditEvent": {
        "event_id": "55555555-5555-4555-8555-555555555551",
        "event_type": "brief.confirmed",
        "occurred_at": "2026-07-19T03:04:00Z",
        "summary": "Teacher confirmed receipt of the English language arts brief.",
        "actor": {"actor_ref": "teacher-nguyen", "actor_role": "teacher"},
        "subject": {"subject_type": "brief", "subject_ref": "brief-ela-03"},
        "changes": [
            {"field_path": "status", "previous_value": "released", "new_value": "confirmed"}
        ],
        "evidence": [
            {
                "evidence_type": "document",
                "evidence_ref": "brief-ela-03",
                "locator": None,
            }
        ],
        "correlation_id": "55555555-5555-4555-8555-555555555552",
        "run_id": None,
    },
    "PipelineStatusEvent": {
        "run_id": "66666666-6666-4666-8666-666666666661",
        "seq": 4,
        "stage": "extract",
        "agent_label": "Extraction Agent",
        "state": "running",
        "detail": "Structuring 12 approved pages into the IEP record contract.",
        "progress": 0.5,
        "parent_stage": None,
        "ts": "2026-07-19T03:05:00Z",
    },
}

MODEL_TYPES: dict[str, type[BaseModel]] = {
    "IEPRecord": IEPRecord,
    "ObligationSet": ObligationSet,
    "TeacherBrief": TeacherBrief,
    "ProgressSignal": ProgressSignal,
    "AuditEvent": AuditEvent,
    "PipelineStatusEvent": PipelineStatusEvent,
}


def assert_described_closed_objects(node: object) -> None:
    """Recursively enforce descriptions, required fields, and closed model objects."""

    if isinstance(node, list):
        for item in node:
            assert_described_closed_objects(item)
        return
    if not isinstance(node, dict):
        return
    if node.get("type") == "object" and "properties" in node:
        properties = node["properties"]
        assert isinstance(properties, dict)
        assert node.get("additionalProperties") is False
        assert set(node.get("required", [])) == set(properties)
        for field_schema in properties.values():
            assert isinstance(field_schema, dict)
            description = field_schema.get("description")
            assert isinstance(description, str) and description.strip()
    for value in node.values():
        assert_described_closed_objects(value)


@pytest.mark.parametrize("schema_name", sorted(SAMPLES))
def test_schema_objects_are_closed_required_and_described(schema_name: str) -> None:
    """Every modeled JSON object rejects drift and documents every required field."""

    schema = json.loads((SCHEMA_DIRECTORY / f"{schema_name}.json").read_text())
    assert_described_closed_objects(schema)


@pytest.mark.parametrize("schema_name", sorted(SAMPLES))
def test_json_schema_and_pydantic_round_trip(schema_name: str) -> None:
    """Validate one sample against JSON Schema and round-trip its Pydantic model."""

    sample = SAMPLES[schema_name]
    schema = json.loads((SCHEMA_DIRECTORY / f"{schema_name}.json").read_text())
    assert schema["title"] == schema_name

    model_type = MODEL_TYPES[schema_name]
    validated = model_type.model_validate_json(json.dumps(sample))
    round_tripped = model_type.model_validate_json(validated.model_dump_json())

    assert validated == round_tripped
    print(f"{schema_name}: JSON_SCHEMA_PARSED=PASS PYDANTIC_ROUND_TRIP=PASS")


@pytest.mark.parametrize(
    ("numeric_value", "text_value"),
    [(None, None), (72.0, "doing well")],
)
def test_measurement_requires_exactly_one_value(
    numeric_value: float | None, text_value: str | None
) -> None:
    """The model validator rejects empty and ambiguous deterministic imports."""

    with pytest.raises(ValidationError, match="exactly one"):
        Measurement.model_validate(
            {
                "metric": "main_idea_accuracy",
                "numeric_value": numeric_value,
                "text_value": text_value,
                "unit": "percent",
            }
        )


def test_field_confidences_accepts_boundary_values() -> None:
    """Both inclusive confidence boundaries round-trip without coercion."""

    confidences = FieldConfidences(
        student_ref=0.0,
        disability_category=1.0,
        school_year=0.0,
        annual_review=1.0,
        triennial_reeval=0.0,
        last_progress_report=1.0,
    )

    assert FieldConfidences.model_validate_json(confidences.model_dump_json()) == confidences


def test_field_confidences_rejects_missing_key() -> None:
    """Every canonical scalar and date confidence is required."""

    sample = dict(SAMPLES["IEPRecord"]["field_confidences"])
    sample.pop("last_progress_report")

    with pytest.raises(ValidationError, match="last_progress_report"):
        FieldConfidences.model_validate(sample)


def test_field_confidences_rejects_additional_property() -> None:
    """Unknown confidence fields cannot silently drift the contract."""

    sample = {
        **SAMPLES["IEPRecord"]["field_confidences"],
        "unreviewed_field": 0.9,
    }

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        FieldConfidences.model_validate(sample)


def test_field_confidences_rejects_value_below_zero() -> None:
    """Confidence values below the inclusive lower bound are rejected."""

    sample = dict(SAMPLES["IEPRecord"]["field_confidences"])
    sample["student_ref"] = -0.01

    with pytest.raises(ValidationError, match="greater than or equal to 0"):
        FieldConfidences.model_validate(sample)


def test_field_confidences_rejects_value_above_one() -> None:
    """Confidence values above the inclusive upper bound are rejected."""

    sample = dict(SAMPLES["IEPRecord"]["field_confidences"])
    sample["annual_review"] = 1.01

    with pytest.raises(ValidationError, match="less than or equal to 1"):
        FieldConfidences.model_validate(sample)


def test_accommodation_scope_references_are_required() -> None:
    """An absent scope cannot silently broaden to every class."""

    sample = {**SAMPLES["IEPRecord"]["accommodations"][0], "applies_to_refs": []}

    with pytest.raises(ValidationError, match="at least 1 item"):
        Accommodation.model_validate_json(json.dumps(sample))


def test_all_scope_is_exclusive() -> None:
    """Unconstrained all cannot coexist with a narrowing reference."""

    sample = dict(SAMPLES["IEPRecord"]["accommodations"][0])
    sample["applies_to_refs"] = [
        *sample["applies_to_refs"],
        {
            "scope": "subject",
            "ref": "Mathematics",
            "source_page": 7,
            "source_quote": "in Mathematics",
            "confidence": 0.98,
        },
    ]

    with pytest.raises(ValidationError, match="all scope must be the only"):
        Accommodation.model_validate_json(json.dumps(sample))


def test_scope_references_reject_normalized_duplicates() -> None:
    """Case and whitespace variants cannot create duplicate applicability evidence."""

    sample = dict(SAMPLES["IEPRecord"]["accommodations"][0])
    sample["applies_to_refs"] = [
        {
            "scope": "subject",
            "ref": "Mathematics",
            "source_page": 7,
            "source_quote": "in Mathematics",
            "confidence": 0.98,
        },
        {
            "scope": "subject",
            "ref": "  MATHEMATICS ",
            "source_page": 8,
            "source_quote": "Mathematics classes",
            "confidence": 0.95,
        },
    ]

    with pytest.raises(ValidationError, match="semantically unique"):
        Accommodation.model_validate_json(json.dumps(sample))


def test_structured_output_schema_has_no_conditionals() -> None:
    """Cross-field applicability rules live only in the Pydantic validator."""

    schema = json.loads((SCHEMA_DIRECTORY / "IEPRecord.json").read_text())

    def keys(node: object) -> set[str]:
        if isinstance(node, dict):
            return set(node) | set().union(*(keys(value) for value in node.values()))
        if isinstance(node, list):
            return set().union(*(keys(value) for value in node))
        return set()

    assert not {"allOf", "if", "then", "else"} & keys(schema)


def test_accommodation_obligation_requires_scope_provenance() -> None:
    """An accommodation UUID alone cannot explain why an assignee acquired the duty."""

    sample = json.loads(json.dumps(SAMPLES["ObligationSet"]))
    sample["obligations"][0]["scope_provenance"] = []

    with pytest.raises(ValidationError, match="require scope_provenance"):
        ObligationSet.model_validate_json(json.dumps(sample))


RECONCILIATION_CASES: list[tuple[type[BaseModel], dict[str, Any], str | None]] = [
    (Accommodation, SAMPLES["IEPRecord"]["accommodations"][0], "matched"),
    (Service, SAMPLES["IEPRecord"]["services"][0], "new"),
    (Goal, SAMPLES["IEPRecord"]["goals"][0], "ambiguous"),
    (
        Accommodation,
        {
            **SAMPLES["IEPRecord"]["accommodations"][0],
            "reconciliation_status": None,
        },
        None,
    ),
]


@pytest.mark.parametrize(("model_type", "sample", "expected"), RECONCILIATION_CASES)
def test_reconciliation_status_round_trip(
    model_type: type[BaseModel], sample: dict[str, Any], expected: str | None
) -> None:
    """Every approved reconciliation state, including first-extraction null, round-trips."""

    validated = model_type.model_validate_json(json.dumps(sample))
    round_tripped = model_type.model_validate_json(validated.model_dump_json())

    assert validated == round_tripped
    assert round_tripped.model_dump(mode="json")["reconciliation_status"] == expected
    print(f"reconciliation_status={expected!r}: PYDANTIC_ROUND_TRIP=PASS")
