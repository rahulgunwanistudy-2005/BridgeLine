"""Thin API boundary for starting IEP ingestion runs."""

from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from pydantic import BaseModel, ConfigDict

from bridgeline.config import get_settings
from bridgeline.db.session import async_session_factory
from bridgeline.ingest.normalize import OversizeUploadError
from bridgeline.ingest.persistence import SQLAlchemyIngestStore
from bridgeline.ingest.pipeline import IngestPipeline
from bridgeline.ingest.status import LoggingStatusEventBus
from bridgeline.llm.client import GeminiGateway

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ieps", tags=["ieps"])


class UploadResponse(BaseModel):
    """Acknowledgement for an asynchronously scheduled ingest run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: UUID


def get_ingest_pipeline() -> IngestPipeline:
    """Compose ingest dependencies at the application edge."""

    settings = get_settings()
    return IngestPipeline(
        settings=settings,
        gateway=GeminiGateway.from_settings(settings),
        store=SQLAlchemyIngestStore(async_session_factory),
        event_bus=LoggingStatusEventBus(),
    )


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_iep(
    background_tasks: BackgroundTasks,
    file: Annotated[UploadFile, File(description="PDF, DOCX, or page image")],
    pipeline: Annotated[IngestPipeline, Depends(get_ingest_pipeline)],
    lineage_hint: Annotated[
        UUID | None,
        Form(description="Existing iep_record_id selected by the case manager"),
    ] = None,
) -> UploadResponse:
    """Bound upload size, persist a run, and schedule provider-backed processing."""

    settings = get_settings()
    data = await file.read(settings.ingest_max_upload_bytes + 1)
    await file.close()
    if len(data) > settings.ingest_max_upload_bytes:
        error = OversizeUploadError(
            f"Upload exceeds the configured limit of {settings.ingest_max_upload_bytes} bytes"
        )
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(error))
    if not data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Upload is empty"
        )

    run_id = uuid4()
    await pipeline.create_run(run_id)
    background_tasks.add_task(
        _run_in_background,
        pipeline,
        data,
        filename=file.filename or "upload",
        run_id=run_id,
        lineage_hint=lineage_hint,
    )
    return UploadResponse(run_id=run_id)


async def _run_in_background(
    pipeline: IngestPipeline,
    data: bytes,
    *,
    filename: str,
    run_id: UUID,
    lineage_hint: UUID | None,
) -> None:
    """Keep a typed pipeline error in run state without crashing the ASGI task runner."""

    try:
        await pipeline.run(
            data,
            filename=filename,
            run_id=run_id,
            lineage_hint=lineage_hint,
        )
    except Exception:
        logger.exception("ingest pipeline failed run_id=%s", run_id)
