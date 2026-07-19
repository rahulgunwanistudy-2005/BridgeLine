"""Tests for lossless canonical IEPRecord persistence payloads."""

from bridgeline.ingest.persistence import serialize_record_payload

from .conftest import sample_record


def test_persistence_payload_retains_required_field_confidences() -> None:
    """The JSONB payload cannot silently drop canonical scalar confidence evidence."""

    record = sample_record()

    payload = serialize_record_payload(record)

    assert payload["field_confidences"] == record.field_confidences.model_dump(mode="json")
