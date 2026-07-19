"""Service readiness endpoint."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from bridgeline.db.session import get_session

router = APIRouter(tags=["system"])


class HealthResponse(BaseModel):
    """Readiness response returned when all required services are available."""

    status: Literal["ok"]
    database: Literal["ok"]


@router.get("/health", response_model=HealthResponse)
async def health(session: Annotated[AsyncSession, Depends(get_session)]) -> HealthResponse:
    """Report readiness after verifying database connectivity."""

    try:
        await session.execute(text("SELECT 1"))
    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable",
        ) from error
    return HealthResponse(status="ok", database="ok")
