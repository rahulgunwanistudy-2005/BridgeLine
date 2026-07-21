"""Temporary slice-one composition for the observable stub pipeline."""

from __future__ import annotations

from functools import lru_cache

from bridgeline.db.session import async_session_factory
from bridgeline.orchestrator.bus import PipelineEventBus
from bridgeline.orchestrator.pipeline import PipelineDefinition, PipelineRunner, StubStage
from bridgeline.orchestrator.store import SQLAlchemyPipelineStore


@lru_cache
def get_stub_pipeline_runner() -> PipelineRunner:
    """Compose one process-local fan-out hub over durable PostgreSQL storage."""

    store = SQLAlchemyPipelineStore(async_session_factory)
    bus = PipelineEventBus(store)
    definition = PipelineDefinition(
        (
            StubStage(name="ingest", agent_label="Ingest Agent"),
            StubStage(
                name="extract",
                agent_label="Extraction Agent",
                depends_on=("ingest",),
            ),
        )
    )
    return PipelineRunner(definition=definition, store=store, bus=bus)
