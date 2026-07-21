"""Real cx/01 ingest operations exposed as explicit, observable DAG stages."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import cast
from uuid import UUID, uuid4

from bridgeline.config import Settings
from bridgeline.db.schemas import IEPRecord, PipelineState
from bridgeline.ingest.extract import IEPExtractor
from bridgeline.ingest.gate import (
    ConfidenceGate,
    DocumentClassification,
    GateResult,
    reject_non_iep,
)
from bridgeline.ingest.identity import reconcile_identities
from bridgeline.ingest.normalize import normalize_document
from bridgeline.ingest.ocr import OCRPage, OCRProcessor, StructuredGateway
from bridgeline.ingest.persistence import IngestStore
from bridgeline.orchestrator.pipeline import (
    PipelineContext,
    StageCompleted,
    StageErrorPolicy,
    StagePaused,
)


@dataclass(frozen=True, slots=True)
class IngestStage:
    """Normalize, OCR, and classify input before structured extraction."""

    settings: Settings
    gateway: StructuredGateway
    name: str = "ingest"
    agent_label: str = "Ingest Agent"
    depends_on: tuple[str, ...] = ()
    on_error: StageErrorPolicy = field(default_factory=StageErrorPolicy)

    async def run(self, ctx: PipelineContext) -> StageCompleted:
        data = cast(bytes, ctx.values["upload_data"])
        filename = cast(str, ctx.values["filename"])
        document = await asyncio.to_thread(
            normalize_document,
            data,
            filename=filename,
            max_upload_bytes=self.settings.ingest_max_upload_bytes,
            pdf_dpi=self.settings.ingest_pdf_dpi,
        )
        pages = await OCRProcessor(
            gateway=self.gateway, page_concurrency=self.settings.ingest_ocr_page_concurrency
        ).process(document)
        classification = await reject_non_iep(
            pages,
            gateway=self.gateway,
            rejection_confidence=self.settings.ingest_non_iep_rejection_confidence,
        )
        ctx.values.update(document=document, pages=pages, classification=classification)
        return StageCompleted(
            detail=f"Prepared {len(document.pages)} source page(s) with OCR and IEP preflight."
        )


@dataclass(frozen=True, slots=True)
class ExtractStage:
    """Create and persist the validated, immutable draft IEP version."""

    settings: Settings
    gateway: StructuredGateway
    store: IngestStore
    name: str = "extract"
    agent_label: str = "Extraction Agent"
    depends_on: tuple[str, ...] = ("ingest",)
    on_error: StageErrorPolicy = field(default_factory=StageErrorPolicy)

    async def run(self, ctx: PipelineContext) -> StageCompleted:
        pages = cast(tuple[OCRPage, ...], ctx.values["pages"])
        lineage_hint = cast(UUID | None, ctx.values.get("lineage_hint"))
        lineage_id = lineage_hint or uuid4()
        extraction = await IEPExtractor(
            gateway=self.gateway, pages_per_chunk=self.settings.ingest_extraction_pages_per_chunk
        ).extract(pages, iep_record_id=lineage_id, run_id=ctx.run_id)
        prior = await self.store.get_prior_approved(lineage_id) if lineage_hint else None
        record = reconcile_identities(extraction.record, prior)
        persisted_id = await self.store.save_draft(record, ctx.run_id)
        ctx.values.update(record=record, persisted_id=persisted_id)
        return StageCompleted(
            detail="Validated the source-grounded IEPRecord contract and saved an immutable draft."
        )


@dataclass(frozen=True, slots=True)
class ConfidenceGateStage:
    """Turn confidence and identity evidence into explicit review instructions."""

    settings: Settings
    name: str = "confidence_gate"
    agent_label: str = "Confidence Gate"
    depends_on: tuple[str, ...] = ("extract",)
    on_error: StageErrorPolicy = field(default_factory=StageErrorPolicy)

    async def run(self, ctx: PipelineContext) -> StageCompleted:
        record = cast(IEPRecord, ctx.values["record"])
        classification = cast(DocumentClassification, ctx.values["classification"])
        gate = ConfidenceGate(
            field_threshold=self.settings.ingest_field_confidence_threshold,
            legibility_threshold=self.settings.ingest_legibility_threshold,
        ).evaluate(record, classification)
        ctx.values["gate"] = gate
        if gate.review_fields:
            return StageCompleted(
                state=PipelineState.NEEDS_REVIEW,
                detail=f"Flagged {len(gate.review_fields)} field(s) for case-manager review.",
            )
        return StageCompleted(detail="All confidence checks passed with source evidence preserved.")


@dataclass(frozen=True, slots=True)
class HumanApprovalStage:
    """First-class intentional pause; no task remains alive while the run is parked."""

    name: str = "human_approval"
    agent_label: str = "Case Manager Review"
    depends_on: tuple[str, ...] = ("confidence_gate",)
    on_error: StageErrorPolicy = field(default_factory=StageErrorPolicy)

    async def run(self, ctx: PipelineContext) -> StagePaused:
        gate = cast(GateResult, ctx.values["gate"])
        persisted_id = cast(UUID, ctx.values["persisted_id"])
        return StagePaused(
            detail=(
                "Awaiting case-manager approval. Review the source-grounded IEP draft and any "
                "highlighted fields before Bridgeline derives teacher obligations."
            ),
            attention_kind="human_approval",
            attention_payload={
                "draft_id": str(persisted_id),
                "review_fields": [field.model_dump(mode="json") for field in gate.review_fields],
            },
        )
