"""Explicit DAG runner used by the observable processing pipeline."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Literal, Protocol
from uuid import UUID

from bridgeline.db.schemas import PipelineState
from bridgeline.orchestrator.bus import PipelineEventBus
from bridgeline.orchestrator.store import PipelineStore

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class StageErrorPolicy:
    """Declared error behavior; later slices add review and retry policies."""

    retry_attempts: int = 0
    terminal_state: PipelineState = PipelineState.ERROR


@dataclass(slots=True)
class PipelineContext:
    """Run-local stage data; persistent artifacts are introduced by real stages."""

    run_id: UUID
    values: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class StageCompleted:
    """A stage result that can surface reviewable findings without stopping the DAG."""

    detail: str
    state: PipelineState = PipelineState.DONE


@dataclass(frozen=True, slots=True)
class StagePaused:
    """An intentional human-in-the-loop pause with durable review instructions."""

    detail: str
    attention_kind: Literal["human_approval", "model_uncertainty", "system_failure"]
    attention_payload: dict[str, object]
    retryable: bool = False


class PipelineStage(Protocol):
    """A named DAG node with UI copy and explicit failure semantics."""

    @property
    def name(self) -> str: ...

    @property
    def agent_label(self) -> str: ...

    @property
    def depends_on(self) -> tuple[str, ...]: ...

    @property
    def on_error(self) -> StageErrorPolicy: ...

    async def run(self, ctx: PipelineContext) -> StageCompleted | StagePaused: ...


@dataclass(frozen=True, slots=True)
class StubStage:
    """Deterministic slice-one stage that makes the runner visible without provider calls."""

    name: str
    agent_label: str
    depends_on: tuple[str, ...] = ()
    on_error: StageErrorPolicy = StageErrorPolicy()
    delay_seconds: float = 0.35

    async def run(self, ctx: PipelineContext) -> StageCompleted:
        await asyncio.sleep(self.delay_seconds)
        ctx.values[self.name] = "completed"
        return StageCompleted(detail=f"{self.agent_label} completed its work.")


class PipelineDefinition:
    """Validated, acyclic stage graph with deterministic topological ordering."""

    def __init__(self, stages: tuple[PipelineStage, ...]) -> None:
        if not stages:
            raise ValueError("pipeline requires at least one stage")
        self._stages = {stage.name: stage for stage in stages}
        if len(self._stages) != len(stages):
            raise ValueError("pipeline stage names must be unique")
        for stage in stages:
            unknown = set(stage.depends_on) - self._stages.keys()
            if unknown:
                raise ValueError(f"stage {stage.name} has unknown dependencies: {sorted(unknown)}")
        self._ordered = self._topological_order(stages)

    @property
    def stages(self) -> tuple[PipelineStage, ...]:
        return self._ordered

    def _topological_order(self, stages: tuple[PipelineStage, ...]) -> tuple[PipelineStage, ...]:
        remaining = {stage.name: set(stage.depends_on) for stage in stages}
        ordered: list[PipelineStage] = []
        while remaining:
            ready = [
                stage for stage in stages if stage.name in remaining and not remaining[stage.name]
            ]
            if not ready:
                raise ValueError("pipeline stage graph contains a cycle")
            for stage in ready:
                ordered.append(stage)
                remaining.pop(stage.name)
                for dependencies in remaining.values():
                    dependencies.discard(stage.name)
        return tuple(ordered)


class PipelineRunner:
    """Runs an explicit DAG while making each stage observable and durable."""

    def __init__(
        self,
        *,
        definition: PipelineDefinition,
        store: PipelineStore,
        bus: PipelineEventBus,
    ) -> None:
        self._definition = definition
        self._store = store
        self._bus = bus

    @property
    def bus(self) -> PipelineEventBus:
        return self._bus

    async def create_run(self, run_id: UUID) -> None:
        await self._store.create_run(run_id, detail="Demo pipeline queued for execution.")
        for stage in self._definition.stages:
            await self._bus.emit(
                run_id=run_id,
                stage=stage.name,
                agent_label=stage.agent_label,
                state=PipelineState.QUEUED,
                detail=f"{stage.agent_label} is ready to begin.",
            )

    async def run(self, run_id: UUID, *, values: dict[str, object] | None = None) -> None:
        """Run each current DAG node; real stage recovery is added in slice two."""

        ctx = PipelineContext(run_id=run_id, values={} if values is None else values)
        for stage in self._definition.stages:
            await self._store.set_run_state(
                run_id,
                state="running",
                stage=stage.name,
                detail=f"{stage.agent_label} is working.",
            )
            await self._bus.emit(
                run_id=run_id,
                stage=stage.name,
                agent_label=stage.agent_label,
                state=PipelineState.RUNNING,
                detail=f"{stage.agent_label} is working.",
            )
            result = await stage.run(ctx)
            if isinstance(result, StagePaused):
                await self._store.set_attention(
                    run_id,
                    kind=result.attention_kind,
                    payload=result.attention_payload,
                    retryable=result.retryable,
                )
                await self._store.set_run_state(
                    run_id,
                    state="awaiting_approval",
                    stage=stage.name,
                    detail=result.detail,
                )
                await self._bus.emit(
                    run_id=run_id,
                    stage=stage.name,
                    agent_label=stage.agent_label,
                    state=PipelineState.NEEDS_REVIEW,
                    detail=result.detail,
                    progress=1.0,
                )
                return
            is_last = stage is self._definition.stages[-1]
            await self._store.set_run_state(
                run_id,
                state="done" if is_last else "running",
                stage=stage.name,
                detail=result.detail,
            )
            await self._bus.emit(
                run_id=run_id,
                stage=stage.name,
                agent_label=stage.agent_label,
                state=result.state,
                detail=result.detail,
                progress=1.0,
            )

    async def run_safely(self, run_id: UUID, *, values: dict[str, object] | None = None) -> None:
        """Ensure a background-task failure is logged rather than disappearing."""

        try:
            await self.run(run_id, values=values)
        except Exception:
            logger.exception("pipeline runner failed run_id=%s", run_id)
            raise
