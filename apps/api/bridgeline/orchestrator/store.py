"""Durable persistence operations for pipeline lifecycle and status events."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol, cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bridgeline.db.models import PipelineRun
from bridgeline.db.models import PipelineStatusEvent as PipelineStatusEventRow
from bridgeline.db.schemas import PipelineState, PipelineStatusEvent


class PipelineStore(Protocol):
    """Persistence surface shared by the runner, bus, and SSE endpoint."""

    async def create_run(self, run_id: UUID, *, detail: str) -> None: ...

    async def set_run_state(
        self, run_id: UUID, *, state: str, stage: str | None, detail: str
    ) -> None: ...

    async def append_event(
        self,
        *,
        run_id: UUID,
        stage: str,
        agent_label: str,
        state: PipelineState,
        detail: str,
        progress: float | None,
        parent_stage: str | None,
    ) -> PipelineStatusEvent: ...

    async def events_after(
        self, run_id: UUID, *, after_seq: int
    ) -> tuple[PipelineStatusEvent, ...]: ...

    async def run_state(self, run_id: UUID) -> str | None: ...


class SQLAlchemyPipelineStore:
    """Short-transaction PostgreSQL store with locked, run-local sequence allocation."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create_run(self, run_id: UUID, *, detail: str) -> None:
        async with self._session_factory.begin() as session:
            session.add(PipelineRun(id=run_id, state="queued", detail=detail))

    async def set_run_state(
        self, run_id: UUID, *, state: str, stage: str | None, detail: str
    ) -> None:
        async with self._session_factory.begin() as session:
            run = await session.get(PipelineRun, run_id)
            if run is None:
                raise LookupError(f"pipeline run {run_id} does not exist")
            run.state = state  # type: ignore[assignment]
            run.current_stage = stage
            run.detail = detail
            now = datetime.now(UTC)
            if state == "running" and run.started_at is None:
                run.started_at = now
            if state in {"done", "error"}:
                run.completed_at = now

    async def append_event(
        self,
        *,
        run_id: UUID,
        stage: str,
        agent_label: str,
        state: PipelineState,
        detail: str,
        progress: float | None,
        parent_stage: str | None,
    ) -> PipelineStatusEvent:
        """Commit an event before any live subscriber is notified."""

        now = datetime.now(UTC)
        async with self._session_factory.begin() as session:
            run = (
                await session.execute(
                    select(PipelineRun).where(PipelineRun.id == run_id).with_for_update()
                )
            ).scalar_one_or_none()
            if run is None:
                raise LookupError(f"pipeline run {run_id} does not exist")
            run.next_event_seq += 1
            row = PipelineStatusEventRow(
                run_id=run_id,
                seq=run.next_event_seq,
                stage=stage,
                agent_label=agent_label,
                state=state.value,
                detail=detail,
                progress=progress,
                parent_stage=parent_stage,
                ts=now,
            )
            session.add(row)
            await session.flush()
            return _event_from_row(row)

    async def events_after(
        self, run_id: UUID, *, after_seq: int
    ) -> tuple[PipelineStatusEvent, ...]:
        async with self._session_factory() as session:
            rows = (
                await session.scalars(
                    select(PipelineStatusEventRow)
                    .where(
                        PipelineStatusEventRow.run_id == run_id,
                        PipelineStatusEventRow.seq > after_seq,
                    )
                    .order_by(PipelineStatusEventRow.seq)
                )
            ).all()
        return tuple(_event_from_row(row) for row in rows)

    async def run_state(self, run_id: UUID) -> str | None:
        async with self._session_factory() as session:
            state = await session.scalar(select(PipelineRun.state).where(PipelineRun.id == run_id))
        return None if state is None else cast(str, state)


def _event_from_row(row: PipelineStatusEventRow) -> PipelineStatusEvent:
    return PipelineStatusEvent(
        run_id=row.run_id,
        seq=row.seq,
        stage=row.stage,
        agent_label=row.agent_label,
        state=PipelineState(row.state),
        detail=row.detail,
        progress=row.progress,
        parent_stage=row.parent_stage,
        ts=row.ts,
    )
