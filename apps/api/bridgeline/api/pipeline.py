"""SSE boundary and development-only stub launcher for the observable pipeline."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict

from bridgeline.config import get_settings
from bridgeline.orchestrator.composition import get_stub_pipeline_runner
from bridgeline.orchestrator.pipeline import PipelineRunner

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


class DemoRunResponse(BaseModel):
    """Acknowledgement for a development-only observable stub run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: UUID


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
    runner: Annotated[PipelineRunner, Depends(get_stub_pipeline_runner)],
    last_event_id: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
) -> StreamingResponse:
    """Replay durable events after Last-Event-ID, then stream committed live additions."""

    cursor = _parse_last_event_id(last_event_id)
    if not await runner.bus.has_run(run_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline run not found")
    return StreamingResponse(
        runner.bus.stream(run_id, last_event_id=cursor),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
