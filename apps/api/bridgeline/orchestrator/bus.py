"""Persist-then-fan-out status bus and lossless SSE event streaming."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Final
from uuid import UUID

from bridgeline.db.schemas import PipelineState, PipelineStatusEvent
from bridgeline.orchestrator.store import PipelineStore

_TERMINAL_STATES: Final = frozenset({"done", "needs_review", "error"})


class PipelineEventBus:
    """Persist events first, then notify each live listener to refill from storage."""

    def __init__(self, store: PipelineStore) -> None:
        self._store = store
        self._subscribers: dict[UUID, set[asyncio.Queue[None]]] = {}
        self._subscribers_lock = asyncio.Lock()

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
        """Durably append before waking streams; a wake-up never carries the event itself."""

        event = await self._store.append_event(
            run_id=run_id,
            stage=stage,
            agent_label=agent_label,
            state=state,
            detail=detail,
            progress=progress,
            parent_stage=parent_stage,
        )
        await self._notify(run_id)
        return event

    async def stream(self, run_id: UUID, *, last_event_id: int | None = None) -> AsyncIterator[str]:
        """Replay durable history after a cursor, then stream live durable additions."""

        cursor = last_event_id or 0
        queue = await self._subscribe(run_id)
        try:
            while True:
                events = await self._store.events_after(run_id, after_seq=cursor)
                for event in events:
                    cursor = event.seq
                    yield _format_sse(event)

                if await self._store.run_state(run_id) in _TERMINAL_STATES:
                    return
                await queue.get()
        finally:
            await self._unsubscribe(run_id, queue)

    async def has_run(self, run_id: UUID) -> bool:
        """Tell the HTTP boundary whether a requested run exists."""

        return await self._store.run_state(run_id) is not None

    async def _subscribe(self, run_id: UUID) -> asyncio.Queue[None]:
        queue: asyncio.Queue[None] = asyncio.Queue(maxsize=1)
        async with self._subscribers_lock:
            self._subscribers.setdefault(run_id, set()).add(queue)
        return queue

    async def _unsubscribe(self, run_id: UUID, queue: asyncio.Queue[None]) -> None:
        async with self._subscribers_lock:
            queues = self._subscribers.get(run_id)
            if queues is None:
                return
            queues.discard(queue)
            if not queues:
                self._subscribers.pop(run_id, None)

    async def _notify(self, run_id: UUID) -> None:
        async with self._subscribers_lock:
            queues = tuple(self._subscribers.get(run_id, ()))
        for queue in queues:
            if not queue.full():
                queue.put_nowait(None)


def _format_sse(event: PipelineStatusEvent) -> str:
    payload = event.model_dump(mode="json")
    return (
        f"id: {event.seq}\n"
        "event: pipeline_status\n"
        f"data: {json.dumps(payload, separators=(',', ':'))}\n\n"
    )
