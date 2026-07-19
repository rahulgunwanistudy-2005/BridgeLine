"""End-to-end normalize → OCR → extract → reconcile → gate → persist pipeline."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from uuid import UUID, uuid4

from bridgeline.config import Settings
from bridgeline.db.schemas import IEPRecord, PipelineState
from bridgeline.ingest.extract import IEPExtractor
from bridgeline.ingest.gate import ConfidenceGate, GateResult, reject_non_iep
from bridgeline.ingest.identity import reconcile_identities
from bridgeline.ingest.normalize import normalize_document
from bridgeline.ingest.ocr import OCRProcessor, StructuredGateway
from bridgeline.ingest.persistence import IngestStore
from bridgeline.ingest.status import StatusEventBus

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PipelineResult:
    """Completed ingest output retained for tests and synchronous callers."""

    record: IEPRecord
    gate: GateResult
    persisted_id: UUID


class IngestPipeline:
    """Coordinate typed stages without leaking provider or database details between them."""

    def __init__(
        self,
        *,
        settings: Settings,
        gateway: StructuredGateway,
        store: IngestStore,
        event_bus: StatusEventBus,
    ) -> None:
        self._settings = settings
        self._gateway = gateway
        self._store = store
        self._events = event_bus
        self._ocr = OCRProcessor(
            gateway=gateway, page_concurrency=settings.ingest_ocr_page_concurrency
        )
        self._extractor = IEPExtractor(
            gateway=gateway, pages_per_chunk=settings.ingest_extraction_pages_per_chunk
        )
        self._gate = ConfidenceGate(
            field_threshold=settings.ingest_field_confidence_threshold,
            legibility_threshold=settings.ingest_legibility_threshold,
        )

    async def create_run(self, run_id: UUID) -> None:
        """Persist the upload acknowledgement before scheduling background work."""

        await self._store.create_run(run_id)

    async def run(
        self,
        data: bytes,
        *,
        filename: str,
        run_id: UUID,
        lineage_hint: UUID | None = None,
    ) -> PipelineResult:
        """Run all ingest slices and surface every failure as an error event."""

        stage = "normalize"
        try:
            await self._store.set_run_state(
                run_id, state="running", stage=stage, detail="Normalizing uploaded document"
            )
            await self._emit(
                run_id,
                stage,
                "Ingest Agent",
                PipelineState.RUNNING,
                "Detecting file type and rendering source pages.",
            )
            document = await asyncio.to_thread(
                normalize_document,
                data,
                filename=filename,
                max_upload_bytes=self._settings.ingest_max_upload_bytes,
                pdf_dpi=self._settings.ingest_pdf_dpi,
            )
            await self._emit(
                run_id,
                stage,
                "Ingest Agent",
                PipelineState.DONE,
                f"Normalized {len(document.pages)} source page(s) with orientation correction.",
                1.0,
            )

            stage = "ocr"
            await self._emit(
                run_id,
                stage,
                "OCR Agent",
                PipelineState.RUNNING,
                "Reading page images and preserving embedded text.",
            )
            pages = await self._ocr.process(document)
            await self._emit(
                run_id,
                stage,
                "OCR Agent",
                PipelineState.DONE,
                f"Cleaned OCR for {len(pages)} page(s) with legibility scores.",
                1.0,
            )

            stage = "classify"
            await self._emit(
                run_id,
                stage,
                "Document Classifier",
                PipelineState.RUNNING,
                "Checking that the upload is an IEP before full extraction.",
            )
            classification = await reject_non_iep(
                pages,
                gateway=self._gateway,
                rejection_confidence=self._settings.ingest_non_iep_rejection_confidence,
            )
            await self._emit(
                run_id,
                stage,
                "Document Classifier",
                PipelineState.DONE,
                "Completed the typed IEP document preflight.",
                1.0,
            )

            stage = "extract"
            await self._emit(
                run_id,
                stage,
                "Extraction Agent",
                PipelineState.RUNNING,
                "Extracting verbatim evidence before normalizing IEP fields.",
            )
            # Only an explicit case-manager hint reuses a lineage; otherwise this UUID is fresh.
            lineage_id = lineage_hint or uuid4()
            extraction = await self._extractor.extract(
                pages, iep_record_id=lineage_id, run_id=run_id
            )
            prior = await self._store.get_prior_approved(lineage_id) if lineage_hint else None
            record = reconcile_identities(extraction.record, prior)
            await self._emit(
                run_id,
                stage,
                "Extraction Agent",
                PipelineState.DONE,
                "Validated the source-grounded IEPRecord contract and reconciled stable item IDs.",
                1.0,
            )

            stage = "confidence_gate"
            await self._emit(
                run_id,
                stage,
                "Confidence Gate",
                PipelineState.RUNNING,
                "Enforcing code-level confidence and identity thresholds.",
            )
            gate = self._gate.evaluate(record, classification)
            gate_state = PipelineState.NEEDS_REVIEW if gate.review_fields else PipelineState.DONE
            detail = (
                f"Flagged {len(gate.review_fields)} field(s) for case-manager review."
                if gate.review_fields
                else "All confidence checks passed without a silent low-confidence field."
            )
            await self._emit(run_id, stage, "Confidence Gate", gate_state, detail, 1.0)

            stage = "persist"
            await self._emit(
                run_id,
                stage,
                "Persistence",
                PipelineState.RUNNING,
                "Saving an immutable draft IEP version.",
            )
            persisted_id = await self._store.save_draft(record, run_id)
            final_state = "needs_review" if gate.review_fields else "done"
            await self._store.set_run_state(run_id, state=final_state, stage=stage, detail=detail)
            await self._emit(
                run_id,
                stage,
                "Persistence",
                PipelineState.DONE,
                "Saved the draft and extraction provenance.",
                1.0,
            )
            return PipelineResult(record=record, gate=gate, persisted_id=persisted_id)
        except Exception as exc:
            safe_detail = str(exc) or type(exc).__name__
            await self._store.set_run_state(run_id, state="error", stage=stage, detail=safe_detail)
            await self._emit(run_id, stage, "Ingest Pipeline", PipelineState.ERROR, safe_detail)
            raise

    async def _emit(
        self,
        run_id: UUID,
        stage: str,
        label: str,
        state: PipelineState,
        detail: str,
        progress: float | None = None,
    ) -> None:
        await self._events.emit(
            run_id=run_id,
            stage=stage,
            agent_label=label,
            state=state,
            detail=detail,
            progress=progress,
        )
