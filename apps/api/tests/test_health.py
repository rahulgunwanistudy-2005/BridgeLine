"""Tests for the readiness endpoint."""

from collections.abc import AsyncIterator
from typing import Any

from httpx import ASGITransport, AsyncClient

from bridgeline.db.session import get_session
from bridgeline.main import create_app


class HealthySession:
    """Small test double for a reachable database session."""

    async def execute(self, statement: object) -> Any:
        """Accept the readiness query without contacting a database."""

        return None


async def healthy_session() -> AsyncIterator[HealthySession]:
    """Provide a database session test double."""

    yield HealthySession()


async def test_health_returns_ok_when_database_is_reachable() -> None:
    """The readiness route reports both application and database health."""

    app = create_app()
    app.dependency_overrides[get_session] = healthy_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}
