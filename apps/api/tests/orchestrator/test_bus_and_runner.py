"""Slice-one proofs for durable replay and explicit DAG visibility."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from bridgeline.db.schemas import PipelineState, PipelineStatusEvent
from bridgeline.ingest.gate import GateResult, GateState, ReviewField
from bridgeline.llm.client import GeminiRequestError, GeminiResponseError
from bridgeline.orchestrator.bus import PipelineEventBus
from bridgeline.orchestrator.pipeline import (
    PipelineContext,
    PipelineDefinition,
    PipelineRunner,
    StageCompleted,
    StageErrorPolicy,
    StubStage,
)
from bridgeline.orchestrator.stages import HumanApprovalStage


class InMemoryPipelineStore:
    """Small durable-store double retaining all events across stream subscriptions."""

    def __init__(self) -> None:
        self.states: dict[UUID, str] = {}
        self.events: dict[UUID, list[PipelineStatusEvent]] = {}
        self.attention: dict[UUID, tuple[str, dict[str, object], bool]] = {}

    async def create_run(self, run_id: UUID, *, detail: str) -> None:
        self.states[run_id] = "queued"
        self.events[run_id] = []

    async def set_run_state(
        self, run_id: UUID, *, state: str, stage: str | None, detail: str
    ) -> None:
        self.states[run_id] = state

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
        event = PipelineStatusEvent.model_validate(
            {
                "run_id": run_id,
                "seq": len(self.events[run_id]) + 1,
                "stage": stage,
                "agent_label": agent_label,
                "state": state,
                "detail": detail,
                "progress": progress,
                "parent_stage": parent_stage,
                "ts": datetime(2026, 7, 21, tzinfo=UTC),
            }
        )
        self.events[run_id].append(event)
        return event

    async def events_after(
        self, run_id: UUID, *, after_seq: int
    ) -> tuple[PipelineStatusEvent, ...]:
        return tuple(event for event in self.events[run_id] if event.seq > after_seq)

    async def run_state(self, run_id: UUID) -> str | None:
        return self.states.get(run_id)

    async def set_attention(
        self, run_id: UUID, *, kind: str, payload: dict[str, object], retryable: bool
    ) -> None:
        self.attention[run_id] = (kind, payload, retryable)


@dataclass(frozen=True, slots=True)
class RevokedGeminiKeyStage:
    """Chaos-test stage which simulates a credential revoked after an earlier stage finished."""

    name: str = "extract"
    agent_label: str = "Extraction Agent"
    depends_on: tuple[str, ...] = ("ingest",)
    on_error: StageErrorPolicy = field(default_factory=StageErrorPolicy)

    async def run(self, ctx: PipelineContext) -> StageCompleted:
        del ctx
        raise GeminiRequestError("Gemini generateContent request failed", status_code=401)


@dataclass(frozen=True, slots=True)
class InvalidModelResponseStage:
    """Proves schema validation failures preserve raw output for a human decision."""

    name: str = "extract"
    agent_label: str = "Extraction Agent"
    depends_on: tuple[str, ...] = ()
    on_error: StageErrorPolicy = field(default_factory=StageErrorPolicy)

    async def run(self, ctx: PipelineContext) -> StageCompleted:
        del ctx
        raise GeminiResponseError(
            "Gemini response failed local Pydantic validation", raw_output="{bad}"
        )


@dataclass(frozen=True, slots=True)
class TimedOutStage:
    """A stage whose timeout policy has an observable, bounded result."""

    name: str = "extract"
    agent_label: str = "Extraction Agent"
    depends_on: tuple[str, ...] = ()
    on_error: StageErrorPolicy = field(
        default_factory=lambda: StageErrorPolicy(timeout_seconds=0.001)
    )

    async def run(self, ctx: PipelineContext) -> StageCompleted:
        del ctx
        await asyncio.sleep(1)
        return StageCompleted(detail="unreachable")


async def _stream_events(bus: PipelineEventBus, run_id: UUID, cursor: int | None) -> list[str]:
    return [chunk async for chunk in bus.stream(run_id, last_event_id=cursor)]


@pytest.mark.asyncio
async def test_last_event_id_replays_only_the_durable_tail_for_each_client() -> None:
    """Two independently resumed streams never depend on an in-memory event cache."""

    store = InMemoryPipelineStore()
    bus = PipelineEventBus(store)
    run_id = uuid4()
    await store.create_run(run_id, detail="Queued")
    for state in (PipelineState.QUEUED, PipelineState.RUNNING, PipelineState.DONE):
        await bus.emit(
            run_id=run_id,
            stage="ingest",
            agent_label="Ingest Agent",
            state=state,
            detail="Visible test event.",
        )
    await store.set_run_state(run_id, state="done", stage="ingest", detail="Done")

    first_client, refreshed_client = (
        await _stream_events(bus, run_id, 1),
        await _stream_events(bus, run_id, 2),
    )

    assert ["id: 2", "id: 3"] == [chunk.splitlines()[0] for chunk in first_client]
    assert ["id: 3"] == [chunk.splitlines()[0] for chunk in refreshed_client]
    assert all("event: pipeline_status" in chunk for chunk in first_client + refreshed_client)


@pytest.mark.asyncio
async def test_runner_emits_a_visible_topological_dag() -> None:
    """Queued/running/done events retain labels and dependency-respecting order."""

    store = InMemoryPipelineStore()
    bus = PipelineEventBus(store)
    runner = PipelineRunner(
        definition=PipelineDefinition(
            (
                StubStage(name="ingest", agent_label="Ingest Agent", delay_seconds=0),
                StubStage(
                    name="extract",
                    agent_label="Extraction Agent",
                    depends_on=("ingest",),
                    delay_seconds=0,
                ),
            )
        ),
        store=store,
        bus=bus,
    )
    run_id = uuid4()

    await runner.create_run(run_id)
    await runner.run(run_id)

    assert [(event.stage, event.state.value) for event in store.events[run_id]] == [
        ("ingest", "queued"),
        ("extract", "queued"),
        ("ingest", "running"),
        ("ingest", "done"),
        ("extract", "running"),
        ("extract", "done"),
    ]
    assert store.states[run_id] == "done"


@pytest.mark.asyncio
async def test_human_approval_parks_without_a_live_background_task() -> None:
    """The approval stage is a durable intentional pause with approved UI copy."""

    store = InMemoryPipelineStore()
    bus = PipelineEventBus(store)
    runner = PipelineRunner(
        definition=PipelineDefinition((HumanApprovalStage(depends_on=()),)), store=store, bus=bus
    )
    run_id = uuid4()
    await runner.create_run(run_id)

    await runner.run(
        run_id,
        values={
            "persisted_id": uuid4(),
            "gate": GateResult(
                state=GateState.NEEDS_REVIEW,
                review_fields=(
                    ReviewField(path="student_ref", confidence=0.6, reason="Low confidence"),
                ),
            ),
        },
    )

    assert store.states[run_id] == "awaiting_approval"
    assert store.attention[run_id][0] == "human_approval"
    assert store.events[run_id][-1].detail == (
        "Awaiting case-manager approval. Review the source-grounded IEP draft and any "
        "highlighted fields before Bridgeline derives teacher obligations."
    )


@pytest.mark.asyncio
async def test_revoked_gemini_key_mid_run_becomes_retryable_system_failure_on_sse() -> None:
    """A 401 after Ingest is amber, terminal, and persisted before a client can resume."""

    store = InMemoryPipelineStore()
    bus = PipelineEventBus(store)
    runner = PipelineRunner(
        definition=PipelineDefinition(
            (
                StubStage(name="ingest", agent_label="Ingest Agent", delay_seconds=0),
                RevokedGeminiKeyStage(),
                StubStage(
                    name="rules",
                    agent_label="Compliance Rules Engine",
                    depends_on=("extract",),
                    delay_seconds=0,
                ),
            )
        ),
        store=store,
        bus=bus,
    )
    run_id = uuid4()
    await runner.create_run(run_id)

    await runner.run_safely(run_id)

    assert store.states[run_id] == "needs_review"
    assert store.attention[run_id] == (
        "system_failure",
        {
            "failure_class": "provider_request",
            "error_type": "gemini_request",
            "status_code": 401,
        },
        True,
    )
    assert [(event.stage, event.state.value) for event in store.events[run_id]] == [
        ("ingest", "queued"),
        ("extract", "queued"),
        ("rules", "queued"),
        ("ingest", "running"),
        ("ingest", "done"),
        ("extract", "running"),
        ("extract", "needs_review"),
    ]
    resumed = await _stream_events(bus, run_id, 5)
    assert len(resumed) == 2
    assert "Gemini authentication failed" in resumed[-1]
    assert "rules\"" not in resumed[-1]


@pytest.mark.asyncio
async def test_schema_validation_failure_is_model_uncertainty_with_raw_output() -> None:
    store = InMemoryPipelineStore()
    bus = PipelineEventBus(store)
    runner = PipelineRunner(
        definition=PipelineDefinition((InvalidModelResponseStage(),)), store=store, bus=bus
    )
    run_id = uuid4()
    await runner.create_run(run_id)

    await runner.run(run_id)

    assert store.states[run_id] == "needs_review"
    assert store.attention[run_id] == (
        "model_uncertainty",
        {
            "failure_class": "schema_validation",
            "error_type": "gemini_response",
            "raw_output": "{bad}",
        },
        True,
    )


@pytest.mark.asyncio
async def test_stage_timeout_becomes_retryable_system_failure() -> None:
    store = InMemoryPipelineStore()
    bus = PipelineEventBus(store)
    runner = PipelineRunner(definition=PipelineDefinition((TimedOutStage(),)), store=store, bus=bus)
    run_id = uuid4()
    await runner.create_run(run_id)

    await runner.run(run_id)

    assert store.states[run_id] == "needs_review"
    assert store.attention[run_id][0] == "system_failure"
    assert store.attention[run_id][1]["failure_class"] == "stage_timeout"
