"""Thin HTTP boundaries for registry inspection and obligation derivation."""

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from bridgeline.config import get_settings
from bridgeline.db.schemas import ObligationSet
from bridgeline.db.session import get_session
from bridgeline.rules.registry import RULES, RULES_VERSION
from bridgeline.rules.repository import ApprovedRecordNotFoundError, RulesRepository

registry_router = APIRouter(prefix="/rules", tags=["rules"])
obligations_router = APIRouter(prefix="/ieps", tags=["rules"])


class RuleResponse(BaseModel):
    """Public, reviewer-readable registry entry."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    citation: str
    description: str


class RegistryResponse(BaseModel):
    """Versioned ordered registry response."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    rules_version: str
    rules: tuple[RuleResponse, ...]


@registry_router.get("", response_model=RegistryResponse)
async def get_registry() -> RegistryResponse:
    """Expose exact registered citations for rapid reviewer verification."""

    return RegistryResponse(
        rules_version=RULES_VERSION,
        rules=tuple(
            RuleResponse(id=rule.id, citation=rule.citation, description=rule.description)
            for rule in RULES
        ),
    )


@obligations_router.post(
    "/{iep_record_id}/obligations/derive",
    response_model=tuple[ObligationSet, ...],
    status_code=status.HTTP_200_OK,
)
async def derive(
    iep_record_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> tuple[ObligationSet, ...]:
    """Derive and idempotently persist obligations for the current approved version."""

    repository = RulesRepository(session)
    now = datetime.now(UTC)
    try:
        timezone = ZoneInfo(get_settings().school_timezone)
    except ZoneInfoNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Configured school timezone is invalid",
        ) from error
    try:
        await repository.derive_and_persist(
            iep_record_id,
            generated_at=now,
            as_of=now.astimezone(timezone).date(),
            derivation_run_id=uuid4(),
        )
        return await repository.obligation_sets(iep_record_id)
    except ApprovedRecordNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@obligations_router.get("/{iep_record_id}/obligations", response_model=tuple[ObligationSet, ...])
async def list_obligations(
    iep_record_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> tuple[ObligationSet, ...]:
    """List obligations for the current approved version in canonical groups."""

    try:
        return await RulesRepository(session).obligation_sets(iep_record_id)
    except ApprovedRecordNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
