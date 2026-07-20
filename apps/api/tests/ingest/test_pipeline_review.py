"""Pipeline conversion of reviewable extraction failures."""

from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

from bridgeline.ingest import pipeline as pipeline_module
from bridgeline.ingest.extract import IncompleteExtractionError
from bridgeline.ingest.gate import GateState
from bridgeline.ingest.pipeline import IngestPipeline, PipelineNeedsReview


class _Store:
    def __init__(self) -> None:
        self.states: list[tuple[str, str | None]] = []

    async def set_run_state(
        self, run_id: object, *, state: str, stage: str | None, detail: str
    ) -> None:
        self.states.append((state, stage))


class _Events:
    async def emit(self, **kwargs: object) -> None:
        return None


class _OCR:
    async def process(self, document: object) -> tuple[()]:
        return ()


class _Extractor:
    async def extract(self, *args: object, **kwargs: object) -> object:
        raise IncompleteExtractionError(("accommodations[0].applies_to_refs",))


@pytest.mark.asyncio
async def test_missing_scope_becomes_typed_needs_review_not_pipeline_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing scope terminates normally as needs_review and is not re-raised."""

    pipeline = object.__new__(IngestPipeline)
    pipeline_any: Any = pipeline
    pipeline_any._settings = SimpleNamespace(
        ingest_max_upload_bytes=1024,
        ingest_pdf_dpi=150,
        ingest_non_iep_rejection_confidence=0.85,
    )
    store = _Store()
    pipeline_any._store = store
    pipeline_any._events = _Events()
    pipeline_any._gateway = object()
    pipeline_any._ocr = _OCR()
    pipeline_any._extractor = _Extractor()
    monkeypatch.setattr(
        pipeline_module,
        "normalize_document",
        lambda *args, **kwargs: SimpleNamespace(pages=()),
    )

    async def classified(*args: object, **kwargs: object) -> object:
        return object()

    monkeypatch.setattr(pipeline_module, "reject_non_iep", classified)

    result = await pipeline.run(
        b"document",
        filename="iep.pdf",
        run_id=uuid4(),
    )

    assert isinstance(result, PipelineNeedsReview)
    assert result.gate.state is GateState.NEEDS_REVIEW
    assert result.gate.review_fields[0].path == "accommodations[0].applies_to_refs"
    assert store.states[-1] == ("needs_review", "confidence_gate")
    assert all(state != "error" for state, _ in store.states)
