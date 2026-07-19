"""Verbatim-first, schema-validated IEP structured extraction."""

from __future__ import annotations

import json
import re
from datetime import UTC, date, datetime
from typing import Annotated
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from bridgeline.db.schemas import (
    Accommodation,
    AppliesTo,
    ExtractionMeta,
    FieldConfidences,
    Goal,
    IEPDates,
    IEPRecord,
    Service,
)
from bridgeline.ingest.ocr import OCRPage, StructuredGateway
from bridgeline.llm.client import GEMINI_MODEL
from bridgeline.llm.prompts import PromptRegistry

Confidence = Annotated[float, Field(ge=0.0, le=1.0)]


class ExtractionError(ValueError):
    """Base class for typed extraction failures."""


class IncompleteExtractionError(ExtractionError):
    """Raised instead of inventing values required by the canonical record contract."""

    def __init__(self, missing_paths: tuple[str, ...]) -> None:
        super().__init__(
            "IEP extraction is incomplete and requires review: " + ", ".join(missing_paths)
        )
        self.missing_paths = missing_paths


class ExtractedAccommodation(BaseModel):
    """Source-grounded accommodation before stable ID assignment."""

    model_config = ConfigDict(extra="forbid", strict=True)

    text: str | None
    applies_to: list[AppliesTo]
    source_page: int | None = Field(ge=1)
    source_quote: str | None
    confidence: Confidence


class ExtractedService(BaseModel):
    """Source-grounded service before stable ID assignment."""

    model_config = ConfigDict(extra="forbid", strict=True)

    type: str | None
    minutes_per_week: int | None = Field(ge=1)
    frequency: str | None
    provider_role: str | None
    start: date | None
    end: date | None
    source_page: int | None = Field(ge=1)
    source_quote: str | None
    confidence: Confidence


class ExtractedGoal(BaseModel):
    """Source-grounded goal before stable ID assignment."""

    model_config = ConfigDict(extra="forbid", strict=True)

    text: str | None
    baseline: str | None
    target: str | None
    measure: str | None
    progress_cadence: str | None
    source_page: int | None = Field(ge=1)
    source_quote: str | None
    confidence: Confidence


class ExtractionDraft(BaseModel):
    """Fail-closed LLM response that can represent absent source fields as null."""

    model_config = ConfigDict(extra="forbid", strict=True)

    student_ref: str | None
    disability_category: str | None
    school_year: str | None
    accommodations: list[ExtractedAccommodation]
    services: list[ExtractedService]
    goals: list[ExtractedGoal]
    annual_review: date | None
    triennial_reeval: date | None
    last_progress_report: date | None
    field_confidences: FieldConfidences


class ExtractionOutput(BaseModel):
    """Canonical record produced by schema-enforced extraction."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    record: IEPRecord


class IEPExtractor:
    """Chunk long documents, merge source-grounded drafts, and build IEPRecord."""

    def __init__(
        self,
        *,
        gateway: StructuredGateway,
        pages_per_chunk: int = 8,
        prompts: PromptRegistry | None = None,
    ) -> None:
        if pages_per_chunk < 1:
            raise ValueError("pages_per_chunk must be positive")
        self._gateway = gateway
        self._pages_per_chunk = pages_per_chunk
        self._prompts = prompts or PromptRegistry()

    async def extract(
        self,
        pages: tuple[OCRPage, ...],
        *,
        iep_record_id: UUID,
        run_id: UUID,
    ) -> ExtractionOutput:
        """Extract chunks and use an evidence-preserving merge for long documents."""

        if not pages:
            raise IncompleteExtractionError(("pages",))
        chunks = [
            pages[index : index + self._pages_per_chunk]
            for index in range(0, len(pages), self._pages_per_chunk)
        ]
        drafts: list[ExtractionDraft] = []
        for chunk in chunks:
            prompt = self._prompts.render("iep_extract", {"pages": _serialize_pages(chunk)})
            result = await self._gateway.generate_structured(
                prompt=prompt,
                response_model=ExtractionDraft,
                max_output_tokens=8192,
                temperature=0.0,
                thinking_level="low",
            )
            drafts.append(result.data)

        if len(drafts) == 1:
            merged = drafts[0]
        else:
            prompt = self._prompts.render(
                "iep_merge",
                {"drafts": json.dumps([draft.model_dump(mode="json") for draft in drafts])},
            )
            result = await self._gateway.generate_structured(
                prompt=prompt,
                response_model=ExtractionDraft,
                max_output_tokens=8192,
                temperature=0.0,
                thinking_level="low",
            )
            merged = result.data

        return _build_output(
            merged,
            iep_record_id=iep_record_id,
            run_id=run_id,
            pages=pages,
        )


def deduplicate_accommodations(items: list[Accommodation]) -> list[Accommodation]:
    """Collapse formatting-only duplicates and retain the strongest grounded item."""

    best: dict[tuple[str, tuple[str, ...]], Accommodation] = {}
    order: list[tuple[str, tuple[str, ...]]] = []
    for item in items:
        key = (_normalize_text(item.text), tuple(sorted(scope.value for scope in item.applies_to)))
        if key not in best:
            order.append(key)
            best[key] = item
        elif item.confidence > best[key].confidence:
            best[key] = item
    return [best[key] for key in order]


def _build_output(
    draft: ExtractionDraft,
    *,
    iep_record_id: UUID,
    run_id: UUID,
    pages: tuple[OCRPage, ...],
) -> ExtractionOutput:
    missing: list[str] = []
    for path, value in (
        ("student_ref", draft.student_ref),
        ("disability_category", draft.disability_category),
        ("school_year", draft.school_year),
    ):
        if value is None or not value.strip():
            missing.append(path)

    accommodations: list[Accommodation] = []
    for index, accommodation_draft in enumerate(draft.accommodations):
        values = (
            accommodation_draft.text,
            accommodation_draft.source_page,
            accommodation_draft.source_quote,
        )
        if any(value is None or (isinstance(value, str) and not value.strip()) for value in values):
            missing.append(f"accommodations[{index}]")
            continue
        if not accommodation_draft.applies_to:
            missing.append(f"accommodations[{index}].applies_to")
            continue
        assert accommodation_draft.text is not None
        assert accommodation_draft.source_page is not None
        assert accommodation_draft.source_quote is not None
        accommodations.append(
            Accommodation(
                id=uuid4(),
                text=accommodation_draft.text,
                applies_to=accommodation_draft.applies_to,
                source_page=accommodation_draft.source_page,
                source_quote=accommodation_draft.source_quote,
                confidence=accommodation_draft.confidence,
                reconciliation_status=None,
            )
        )

    services: list[Service] = []
    for index, service_draft in enumerate(draft.services):
        service_required = (
            service_draft.type,
            service_draft.minutes_per_week,
            service_draft.frequency,
            service_draft.provider_role,
            service_draft.source_page,
            service_draft.source_quote,
        )
        if any(
            value is None or (isinstance(value, str) and not value.strip())
            for value in service_required
        ):
            missing.append(f"services[{index}]")
            continue
        assert service_draft.type is not None
        assert service_draft.minutes_per_week is not None
        assert service_draft.frequency is not None
        assert service_draft.provider_role is not None
        assert service_draft.source_page is not None
        assert service_draft.source_quote is not None
        services.append(
            Service(
                id=uuid4(),
                type=service_draft.type,
                minutes_per_week=service_draft.minutes_per_week,
                frequency=service_draft.frequency,
                provider_role=service_draft.provider_role,
                start=service_draft.start,
                end=service_draft.end,
                source_page=service_draft.source_page,
                source_quote=service_draft.source_quote,
                confidence=service_draft.confidence,
                reconciliation_status=None,
            )
        )

    goals: list[Goal] = []
    for index, goal_draft in enumerate(draft.goals):
        goal_required = (
            goal_draft.text,
            goal_draft.baseline,
            goal_draft.target,
            goal_draft.measure,
            goal_draft.progress_cadence,
            goal_draft.source_page,
            goal_draft.source_quote,
        )
        if any(
            value is None or (isinstance(value, str) and not value.strip())
            for value in goal_required
        ):
            missing.append(f"goals[{index}]")
            continue
        assert goal_draft.text is not None
        assert goal_draft.baseline is not None
        assert goal_draft.target is not None
        assert goal_draft.measure is not None
        assert goal_draft.progress_cadence is not None
        assert goal_draft.source_page is not None
        assert goal_draft.source_quote is not None
        goals.append(
            Goal(
                id=uuid4(),
                text=goal_draft.text,
                baseline=goal_draft.baseline,
                target=goal_draft.target,
                measure=goal_draft.measure,
                progress_cadence=goal_draft.progress_cadence,
                source_page=goal_draft.source_page,
                source_quote=goal_draft.source_quote,
                confidence=goal_draft.confidence,
                reconciliation_status=None,
            )
        )
    if missing:
        raise IncompleteExtractionError(tuple(missing))
    assert draft.student_ref is not None
    assert draft.disability_category is not None
    assert draft.school_year is not None

    record = IEPRecord(
        iep_record_id=iep_record_id,
        student_ref=draft.student_ref,
        disability_category=draft.disability_category,
        school_year=draft.school_year,
        accommodations=deduplicate_accommodations(accommodations),
        services=services,
        goals=goals,
        dates=IEPDates(
            annual_review=draft.annual_review,
            triennial_reeval=draft.triennial_reeval,
            last_progress_report=draft.last_progress_report,
        ),
        field_confidences=draft.field_confidences,
        extraction_meta=ExtractionMeta(
            model=GEMINI_MODEL,
            run_id=run_id,
            page_count=len(pages),
            legibility_scores=[page.legibility_score for page in pages],
            extracted_at=datetime.now(UTC),
        ),
    )
    return ExtractionOutput(record=record)


def _serialize_pages(pages: tuple[OCRPage, ...]) -> str:
    return "\n\n".join(f"=== PAGE {page.page_number} ===\n{page.corrected_text}" for page in pages)


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()
