"""Tests for lineage upload semantics and the cx/03 event-bus seam."""

from typing import cast
from uuid import UUID, uuid4

from httpx import ASGITransport, AsyncClient

from bridgeline.api.ieps import get_ingest_pipeline
from bridgeline.db.schemas import PipelineState
from bridgeline.ingest.pipeline import IngestPipeline
from bridgeline.ingest.status import LoggingStatusEventBus
from bridgeline.main import create_app


class RecordingPipeline:
    """Small API test double recording case-manager lineage selection."""

    def __init__(self) -> None:
        self.created: list[UUID] = []
        self.lineage_hints: list[UUID | None] = []

    async def create_run(self, run_id: UUID) -> None:
        self.created.append(run_id)

    async def run(
        self,
        data: bytes,
        *,
        filename: str,
        run_id: UUID,
        lineage_hint: UUID | None = None,
    ) -> None:
        self.lineage_hints.append(lineage_hint)


async def test_upload_forwards_explicit_lineage_hint() -> None:
    """Only the UUID explicitly selected by a case manager reaches the pipeline."""

    fake = RecordingPipeline()
    app = create_app()
    app.dependency_overrides[get_ingest_pipeline] = lambda: cast(IngestPipeline, fake)
    lineage = uuid4()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/ieps/upload",
            files={"file": ("sample.pdf", b"%PDF-1.4", "application/pdf")},
            data={"lineage_hint": str(lineage)},
        )

    assert response.status_code == 202
    assert UUID(response.json()["run_id"]) == fake.created[0]
    assert fake.lineage_hints == [lineage]


async def test_status_stub_allocates_monotonic_schema_valid_events() -> None:
    """cx/03 can replace the sink without changing callers or event shape."""

    bus = LoggingStatusEventBus()
    run_id = uuid4()

    first = await bus.emit(
        run_id=run_id,
        stage="normalize",
        agent_label="Ingest Agent",
        state=PipelineState.RUNNING,
        detail="Rendering pages.",
    )
    second = await bus.emit(
        run_id=run_id,
        stage="normalize",
        agent_label="Ingest Agent",
        state=PipelineState.DONE,
        detail="Rendered pages.",
        progress=1.0,
    )

    assert (first.seq, second.seq) == (1, 2)
