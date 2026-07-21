"""Temporary slice-one composition for the observable stub pipeline."""

from __future__ import annotations

from functools import lru_cache

from bridgeline.config import get_settings
from bridgeline.db.session import async_session_factory
from bridgeline.ingest.persistence import SQLAlchemyIngestStore
from bridgeline.llm.client import GeminiGateway
from bridgeline.orchestrator.bus import PipelineEventBus
from bridgeline.orchestrator.pipeline import PipelineDefinition, PipelineRunner, StubStage
from bridgeline.orchestrator.stages import (
    ConfidenceGateStage,
    ExtractStage,
    HumanApprovalStage,
    IngestStage,
)
from bridgeline.orchestrator.store import SQLAlchemyPipelineStore


@lru_cache
def get_pipeline_store() -> SQLAlchemyPipelineStore:
    """Return the process-wide store used by runner, API, and stream."""

    return SQLAlchemyPipelineStore(async_session_factory)


@lru_cache
def get_pipeline_bus() -> PipelineEventBus:
    """Keep one local fan-out hub over the durable database log."""

    return PipelineEventBus(get_pipeline_store())


@lru_cache
def get_pipeline_runner() -> PipelineRunner:
    """Compose the first four production stages around the existing cx/01 services."""

    settings = get_settings()
    gateway = GeminiGateway.from_settings(settings)
    ingest_store = SQLAlchemyIngestStore(async_session_factory)
    return PipelineRunner(
        definition=PipelineDefinition(
            (
                IngestStage(settings=settings, gateway=gateway),
                ExtractStage(settings=settings, gateway=gateway, store=ingest_store),
                ConfidenceGateStage(settings=settings),
                HumanApprovalStage(),
            )
        ),
        store=get_pipeline_store(),
        bus=get_pipeline_bus(),
    )


@lru_cache
def get_stub_pipeline_runner() -> PipelineRunner:
    """Compose one process-local fan-out hub over durable PostgreSQL storage."""

    store = get_pipeline_store()
    bus = get_pipeline_bus()
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
