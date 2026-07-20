"""Thin compliance deadline and findings boundaries."""

from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from bridgeline.config import get_settings
from bridgeline.db.session import get_session
from bridgeline.rules.repository import (
    FindingNotFoundError,
    InvalidFindingTransitionError,
    InvalidScopeMappingActorError,
    RulesRepository,
    ScopeReferenceMappingNotFoundError,
)
from bridgeline.rules.types import (
    Deadline,
    DeadlineStatus,
    Finding,
    FindingSeverity,
    FindingStatus,
)

router = APIRouter(prefix="/compliance", tags=["compliance"])
findings_router = APIRouter(prefix="/findings", tags=["compliance"])


class FindingTransitionRequest(BaseModel):
    """Audited finding lifecycle transition request."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: FindingStatus
    actor_ref: str = Field(min_length=1)
    actor_role: Literal["case_manager", "compliance_admin", "teacher", "provider", "system"]


class ScopeAliasRequest(BaseModel):
    """Audited district scope-alias mutation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    school_year: str = Field(pattern=r"^[0-9]{4}-[0-9]{4}$")
    scope: Literal["subject", "context"]
    document_ref: str = Field(min_length=1)
    target_ref: str = Field(min_length=1)
    actor_ref: str = Field(min_length=1)
    actor_role: Literal["compliance_admin"]


class ScopeResolutionRequest(BaseModel):
    """Audited resolution of one IEP-specific scope finding."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    target_ref: str = Field(min_length=1)
    actor_ref: str = Field(min_length=1)
    actor_role: Literal["case_manager"]


class ScopeMappingRevocationRequest(BaseModel):
    """Authorized actor for a reversible mapping revocation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    actor_ref: str = Field(min_length=1)


class ScopeMappingResponse(BaseModel):
    """Stable identifier of an audited scope mapping."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID


@router.get("/deadlines", response_model=tuple[Deadline, ...])
async def list_deadlines(
    session: Annotated[AsyncSession, Depends(get_session)],
    student_ref: Annotated[str | None, Query(min_length=1)] = None,
    deadline_status: DeadlineStatus | None = None,
) -> tuple[Deadline, ...]:
    """List persisted compliance deadlines in stable due-date order."""

    return await RulesRepository(session).deadlines(
        student_ref=student_ref,
        status=None if deadline_status is None else deadline_status.value,
    )


@findings_router.get("", response_model=tuple[Finding, ...])
async def list_findings(
    session: Annotated[AsyncSession, Depends(get_session)],
    student_ref: Annotated[str | None, Query(min_length=1)] = None,
    finding_status: FindingStatus | None = None,
    severity: FindingSeverity | None = None,
    rule_id: Annotated[str | None, Query(min_length=1)] = None,
) -> tuple[Finding, ...]:
    """List findings in stable feed order with dashboard filters."""

    return await RulesRepository(session).findings(
        student_ref=student_ref,
        status=None if finding_status is None else finding_status.value,
        severity=None if severity is None else severity.value,
        rule_id=rule_id,
    )


@findings_router.post("/derive", response_model=tuple[Finding, ...])
async def derive_district_findings(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> tuple[Finding, ...]:
    """Refresh baseline missing-approved-IEP findings from the active roster."""

    now = datetime.now(UTC)
    try:
        as_of = now.astimezone(ZoneInfo(get_settings().school_timezone)).date()
    except ZoneInfoNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Configured school timezone is invalid",
        ) from error
    return await RulesRepository(session).derive_district_findings(
        generated_at=now, as_of=as_of, derivation_run_id=uuid4()
    )


@findings_router.patch("/{finding_id}", response_model=Finding)
async def transition_finding(
    finding_id: UUID,
    request: FindingTransitionRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Finding:
    """Resolve or reopen a finding with an append-only audit event."""

    try:
        return await RulesRepository(session).transition_finding(
            finding_id,
            status=request.status.value,
            actor_ref=request.actor_ref,
            actor_role=request.actor_role,
            occurred_at=datetime.now(UTC),
        )
    except FindingNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except InvalidFindingTransitionError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.post("/scope-aliases", response_model=ScopeMappingResponse)
async def record_scope_alias(
    request: ScopeAliasRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ScopeMappingResponse:
    """Create or reactivate a district-wide scope alias."""

    mapping_id = await RulesRepository(session).record_scope_alias(
        school_year=request.school_year,
        scope=request.scope,
        document_ref=request.document_ref,
        target_ref=request.target_ref,
        actor_ref=request.actor_ref,
        actor_role=request.actor_role,
        occurred_at=datetime.now(UTC),
    )
    return ScopeMappingResponse(id=mapping_id)


@router.delete("/scope-aliases/{alias_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_scope_alias(
    alias_id: UUID,
    request: ScopeMappingRevocationRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    """Revoke a reusable alias while retaining its audit history."""

    try:
        await RulesRepository(session).revoke_scope_alias(
            alias_id,
            actor_ref=request.actor_ref,
            actor_role="compliance_admin",
            occurred_at=datetime.now(UTC),
        )
    except ScopeReferenceMappingNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@findings_router.post("/{finding_id}/scope-resolution", response_model=ScopeMappingResponse)
async def resolve_scope_finding(
    finding_id: UUID,
    request: ScopeResolutionRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ScopeMappingResponse:
    """Resolve one finding without creating a reusable district alias."""

    try:
        mapping_id = await RulesRepository(session).resolve_scope_finding(
            finding_id,
            target_ref=request.target_ref,
            actor_ref=request.actor_ref,
            actor_role=request.actor_role,
            occurred_at=datetime.now(UTC),
        )
    except ScopeReferenceMappingNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except InvalidScopeMappingActorError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    return ScopeMappingResponse(id=mapping_id)


@router.delete("/scope-resolutions/{resolution_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_scope_resolution(
    resolution_id: UUID,
    request: ScopeMappingRevocationRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    """Revoke a case-manager mapping so re-derivation can reopen the finding."""

    try:
        await RulesRepository(session).revoke_scope_resolution(
            resolution_id,
            actor_ref=request.actor_ref,
            actor_role="case_manager",
            occurred_at=datetime.now(UTC),
        )
    except ScopeReferenceMappingNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
