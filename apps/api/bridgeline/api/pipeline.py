"""SSE boundary and development-only stub launcher for the observable pipeline."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict

from bridgeline.config import get_settings
from bridgeline.db.schemas import PipelineState
from bridgeline.orchestrator.bus import PipelineEventBus
from bridgeline.orchestrator.composition import (
    get_pipeline_bus,
    get_pipeline_store,
    get_stub_pipeline_runner,
)
from bridgeline.orchestrator.pipeline import PipelineRunner
from bridgeline.orchestrator.store import (
    PipelineApprovalStateError,
    PipelineDraftNotFoundError,
    PipelineRunNotFoundError,
    PipelineRunSummary,
    SQLAlchemyPipelineStore,
)

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


class DemoRunResponse(BaseModel):
    """Acknowledgement for a development-only observable stub run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: UUID


class AttentionResponse(BaseModel):
    """Why a run needs human attention, separate from its transport state."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: str | None
    payload: dict[str, object] | None
    retryable: bool


class PipelineRunResponse(BaseModel):
    """Current durable state plus safety-significant attention classification."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: UUID
    state: str
    current_stage: str | None
    detail: str
    attention: AttentionResponse


class ApprovalRequest(BaseModel):
    """Explicit case-manager acknowledgement of a persisted IEP draft."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    actor_ref: str


class ApprovalResponse(BaseModel):
    """Idempotent result of accepting a parked HumanApprovalStage."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: UUID
    iep_record_id: UUID
    state: str
    idempotent: bool


def _parse_last_event_id(value: str | None) -> int | None:
    if value is None or not value.strip():
        return None
    try:
        parsed = int(value)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Last-Event-ID must be a positive integer",
        ) from error
    if parsed < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Last-Event-ID must be a positive integer",
        )
    return parsed


@router.post("/demo-runs", response_model=DemoRunResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_demo_run(
    background_tasks: BackgroundTasks,
    runner: Annotated[PipelineRunner, Depends(get_stub_pipeline_runner)],
) -> DemoRunResponse:
    """Start development-only stubs; the upload route replaces this in slice two."""

    if get_settings().app_env != "development":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    run_id = uuid4()
    await runner.create_run(run_id)
    background_tasks.add_task(runner.run_safely, run_id)
    return DemoRunResponse(run_id=run_id)


@router.get("/{run_id}/events")
async def pipeline_events(
    run_id: UUID,
    bus: Annotated[PipelineEventBus, Depends(get_pipeline_bus)],
    last_event_id: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
) -> StreamingResponse:
    """Replay durable events after Last-Event-ID, then stream committed live additions."""

    cursor = _parse_last_event_id(last_event_id)
    if not await bus.has_run(run_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline run not found")
    return StreamingResponse(
        bus.stream(run_id, last_event_id=cursor),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{run_id}", response_model=PipelineRunResponse)
async def get_pipeline_run(
    run_id: UUID,
    store: Annotated[SQLAlchemyPipelineStore, Depends(get_pipeline_store)],
) -> PipelineRunResponse:
    """Expose the paused review payload without conflating uncertainty and system failure."""

    try:
        summary = await store.summary(run_id)
    except PipelineRunNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    return _run_response(summary)


@router.post("/{run_id}/approve", response_model=ApprovalResponse)
async def approve_pipeline_run(
    run_id: UUID,
    request: ApprovalRequest,
    store: Annotated[SQLAlchemyPipelineStore, Depends(get_pipeline_store)],
    bus: Annotated[PipelineEventBus, Depends(get_pipeline_bus)],
) -> ApprovalResponse:
    """Approve exactly one parked draft and make duplicate submissions harmless."""

    if not request.actor_ref.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="actor_ref is required"
        )
    try:
        iep_record_id, idempotent = await store.approve(run_id)
    except PipelineRunNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except PipelineDraftNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except PipelineApprovalStateError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    if not idempotent:
        await bus.emit(
            run_id=run_id,
            stage="human_approval",
            agent_label="Case Manager Review",
            state=PipelineState.DONE,
            detail=(
                "Case-manager approval recorded. The source-grounded draft is ready for "
                "rules derivation."
            ),
            progress=1.0,
        )
    return ApprovalResponse(
        run_id=run_id,
        iep_record_id=iep_record_id,
        state="done",
        idempotent=idempotent,
    )


def _run_response(summary: PipelineRunSummary) -> PipelineRunResponse:
    return PipelineRunResponse(
        run_id=summary.run_id,
        state=summary.state,
        current_stage=summary.current_stage,
        detail=summary.detail,
        attention=AttentionResponse(
            kind=summary.attention_kind,
            payload=summary.attention_payload,
            retryable=summary.retryable,
        ),
    )
