"""Programmatic validation of authored records against the frozen JSON Schemas.

The JSON files in ``packages/schemas`` are the constitution; this module never mutates
them. It validates structural conformance plus the two cross-field rules the schema
cannot express (consecutive school years, one legibility score per page) so authored
ground truth fails loudly here rather than silently downstream.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from synthgen.constants import SCHEMAS_DIR


class RecordValidationError(ValueError):
    """Raised when an authored record violates the frozen contract."""

    def __init__(self, label: str, messages: list[str]) -> None:
        super().__init__(f"{label}: " + "; ".join(messages))
        self.label = label
        self.messages = messages


@lru_cache(maxsize=None)
def _validator(schema_name: str) -> Draft202012Validator:
    schema_path = SCHEMAS_DIR / schema_name
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _cross_field_messages(record: dict[str, Any]) -> list[str]:
    """Rules the JSON Schema cannot express, mirrored from the Pydantic validators."""

    messages: list[str] = []

    school_year = record.get("school_year")
    if isinstance(school_year, str) and "-" in school_year:
        try:
            first, second = (int(part) for part in school_year.split("-"))
            if second != first + 1:
                messages.append("school_year must contain consecutive years")
        except ValueError:
            pass  # pattern violation already reported by the schema validator

    meta = record.get("extraction_meta")
    if isinstance(meta, dict):
        scores = meta.get("legibility_scores")
        page_count = meta.get("page_count")
        if isinstance(scores, list) and isinstance(page_count, int):
            if len(scores) != page_count:
                messages.append("legibility_scores must contain exactly one score per page")

    return messages


def validate_record(record: dict[str, Any], *, label: str, schema_name: str = "IEPRecord.json") -> None:
    """Validate one record; raise RecordValidationError aggregating all problems."""

    validator = _validator(schema_name)
    messages = [
        f"{'/'.join(str(p) for p in error.path) or '<root>'}: {error.message}"
        for error in sorted(validator.iter_errors(record), key=str)
    ]
    messages.extend(_cross_field_messages(record))
    if messages:
        raise RecordValidationError(label, messages)
