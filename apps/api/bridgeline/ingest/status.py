"""Pipeline status-event interface and cx/03-compatible logging stub."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from bridgeline.db.schemas import PipelineState, PipelineStatusEvent

logger = logging.getLogger(__name__)


class StatusEventBus(Protocol):
    """Interface implemented by this stub and the future persist/fan-out bus."""

    async def emit(
        self,
        *,
        run_id: UUID,
        stage: str,
        agent_label: str,
        state: PipelineState,
        detail: str,
        progress: float | None = None,
        parent_stage: str | None = None,
    ) -> PipelineStatusEvent: ...


class LoggingStatusEventBus:
    """Run-local sequencer that logs schema-valid events until cx/03 lands."""

    def __init__(self) -> None:
        self._sequences: dict[UUID, int] = {}
        self._lock = asyncio.Lock()

    async def emit(
        self,
        *,
        run_id: UUID,
        stage: str,
        agent_label: str,
        state: PipelineState,
        detail: str,
        progress: float | None = None,
        parent_stage: str | None = None,
    ) -> PipelineStatusEvent:
        """Allocate a monotonic cursor and emit a fully validated log payload."""

        async with self._lock:
            seq = self._sequences.get(run_id, 0) + 1
            self._sequences[run_id] = seq
        event = PipelineStatusEvent(
            run_id=run_id,
            seq=seq,
            stage=stage,
            agent_label=agent_label,
            state=state,
            detail=detail,
            progress=progress,
            parent_stage=parent_stage,
            ts=datetime.now(UTC),
        )
        logger.info("pipeline_status_event %s", event.model_dump_json())
        return event
