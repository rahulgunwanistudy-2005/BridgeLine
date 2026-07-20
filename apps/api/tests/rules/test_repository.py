"""Persistence invariant tests for audited obligation transitions."""

from datetime import UTC, date, datetime
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from bridgeline.db.models import (
    AuditEvent,
    ComplianceDeadline,
    Finding,
    Obligation,
    ScopeReferenceAlias,
    ServiceDelayReason,
)
from bridgeline.rules.repository import (
    InvalidScopeMappingActorError,
    InvalidServiceDelayReasonActorError,
    RulesRepository,
    _finding_transition_event,
    _sync_deadline,
)
from bridgeline.rules.types import Deadline, DeadlineStatus, SourceKind


async def test_confirm_transition_appends_audit_event_in_same_commit() -> None:
    obligation = Obligation(
        id=UUID("22222222-2222-4222-8222-222222222221"),
        iep_record_version_id=UUID("11111111-1111-4111-8111-111111111111"),
        student_id=UUID("11111111-1111-4111-8111-111111111112"),
        assignee_kind="teacher",
        assignee_ref="teacher-nguyen",
        assignee_role="teacher-of-record",
        context_kind="class",
        context_ref="class-ela",
        subject="English language arts",
        source_kind="accommodation",
        source_ref=UUID("11111111-1111-4111-8111-111111111113"),
        rule_id="teacher-informed-accommodations",
        citation="34 CFR §300.323(d)(2)(ii)",
        action_text="Provide extended time.",
        practice_text=None,
        status="pending",
        confirmed_at=None,
        flag_reason=None,
    )
    session = AsyncMock(spec=AsyncSession)
    session.get.return_value = obligation
    occurred_at = datetime(2026, 7, 20, 3, tzinfo=UTC)

    await RulesRepository(cast(AsyncSession, session)).transition_obligation(
        obligation.id,
        status="confirmed",
        actor_ref="teacher-nguyen",
        actor_role="teacher",
        occurred_at=occurred_at,
    )

    assert obligation.status == "confirmed"
    assert obligation.confirmed_at == occurred_at
    event = session.add.call_args.args[0]
    assert isinstance(event, AuditEvent)
    assert event.event_type == "obligation.confirmed"
    session.commit.assert_awaited_once()


async def test_finding_resolution_appends_audit_event_in_same_commit() -> None:
    finding = Finding(
        id=UUID("44444444-4444-4444-8444-444444444441"),
        iep_record_version_id=UUID("11111111-1111-4111-8111-111111111111"),
        student_ref="RIV-204",
        rule_id="teacher-informed-accommodations",
        citation="34 CFR §300.323(d)(2)(ii)",
        finding_type="accommodation-partially-confirmed",
        severity="critical",
        detected_on=date(2026, 7, 20),
        title="Implementation is incomplete",
        detail="Three classes remain unconfirmed.",
        related_refs={},
        measurements={"confirmed_classes": 3, "total_classes": 6},
        status="open",
        resolved_at=None,
    )
    session = AsyncMock(spec=AsyncSession)
    session.get.return_value = finding
    occurred_at = datetime(2026, 7, 20, 4, tzinfo=UTC)

    result = await RulesRepository(cast(AsyncSession, session)).transition_finding(
        finding.id,
        status="resolved",
        actor_ref="case-manager-patel",
        actor_role="case_manager",
        occurred_at=occurred_at,
    )

    assert result.status.value == "resolved"
    assert finding.resolved_at == occurred_at
    event = session.add.call_args.args[0]
    assert isinstance(event, AuditEvent)
    assert event.event_type == "finding.resolved"
    session.commit.assert_awaited_once()


def test_automatic_reopen_event_identifies_derivation_run_and_cause() -> None:
    finding = Finding(
        id=UUID("44444444-4444-4444-8444-444444444442"),
        iep_record_version_id=UUID("11111111-1111-4111-8111-111111111111"),
        student_ref="RIV-204",
        rule_id="teacher-informed-accommodations",
        citation="34 CFR §300.323(d)(2)(ii)",
        finding_type="accommodation-partially-confirmed",
        severity="critical",
        detected_on=date(2026, 7, 20),
        title="Implementation is incomplete",
        detail="Three classes remain unconfirmed.",
        related_refs={},
        measurements={"confirmed_classes": 3, "total_classes": 6},
        status="open",
        resolved_at=None,
    )
    derivation_run_id = UUID("55555555-5555-4555-8555-555555555551")

    event = _finding_transition_event(
        finding,
        previous="resolved",
        actor_ref="rules-engine",
        actor_role="system",
        occurred_at=datetime(2026, 7, 20, 5, tzinfo=UTC),
        derivation_run_id=derivation_run_id,
        reason="Reopened because three classes remain unconfirmed.",
    )

    assert event.correlation_id == derivation_run_id
    assert event.payload["derivation_run_id"] == str(derivation_run_id)
    assert event.payload["summary"] == "Reopened because three classes remain unconfirmed."


async def test_provider_cannot_record_own_service_delay_reason() -> None:
    session = AsyncMock(spec=AsyncSession)

    with pytest.raises(InvalidServiceDelayReasonActorError):
        await RulesRepository(cast(AsyncSession, session)).record_service_delay_reason(
            iep_record_version_id=UUID("11111111-1111-4111-8111-111111111111"),
            service_id=UUID("66666666-6666-4666-8666-666666666661"),
            reason="Provider-entered exception",
            actor_ref="provider-slp",
            actor_role="provider",
            occurred_at=datetime(2026, 7, 20, 5, tzinfo=UTC),
        )

    session.commit.assert_not_awaited()


async def test_case_manager_can_revoke_reason_with_atomic_audit_event() -> None:
    row = ServiceDelayReason(
        id=UUID("77777777-7777-4777-8777-777777777771"),
        iep_record_version_id=UUID("11111111-1111-4111-8111-111111111111"),
        service_id=UUID("66666666-6666-4666-8666-666666666661"),
        reason="Documented family scheduling request",
        created_by_ref="case-manager-one",
        active=True,
        revoked_at=None,
        revoked_by_ref=None,
    )
    session = AsyncMock(spec=AsyncSession)
    scalar_result = MagicMock()
    scalar_result.one_or_none.return_value = row
    session.scalars.return_value = scalar_result
    occurred_at = datetime(2026, 7, 20, 6, tzinfo=UTC)

    await RulesRepository(cast(AsyncSession, session)).revoke_service_delay_reason(
        iep_record_version_id=row.iep_record_version_id,
        service_id=row.service_id,
        actor_ref="case-manager-two",
        actor_role="case_manager",
        occurred_at=occurred_at,
    )

    assert row.active is False
    assert row.revoked_at == occurred_at
    event = session.add.call_args.args[0]
    assert isinstance(event, AuditEvent)
    assert event.event_type == "service_delay_reason.revoked"
    assert event.actor_role == "case_manager"
    session.commit.assert_awaited_once()


async def test_only_compliance_admin_can_create_reusable_scope_alias() -> None:
    """A case manager cannot promote a one-record decision to district policy."""

    session = AsyncMock(spec=AsyncSession)

    with pytest.raises(InvalidScopeMappingActorError):
        await RulesRepository(cast(AsyncSession, session)).record_scope_alias(
            school_year="2026-2027",
            scope="context",
            document_ref="during testing",
            target_ref="assessment",
            actor_ref="case-manager-one",
            actor_role="case_manager",
            occurred_at=datetime(2026, 7, 20, 6, tzinfo=UTC),
        )

    session.commit.assert_not_awaited()


async def test_compliance_admin_alias_creation_is_audited_atomically() -> None:
    """Reusable context vocabulary changes carry actor and before/after state."""

    session = AsyncMock(spec=AsyncSession)
    scalar_result = MagicMock()
    scalar_result.one_or_none.return_value = None
    session.scalars.return_value = scalar_result
    occurred_at = datetime(2026, 7, 20, 7, tzinfo=UTC)

    alias_id = await RulesRepository(cast(AsyncSession, session)).record_scope_alias(
        school_year="2026-2027",
        scope="context",
        document_ref=" During  Testing ",
        target_ref="assessment",
        actor_ref="compliance-admin-one",
        actor_role="compliance_admin",
        occurred_at=occurred_at,
    )

    added = [call.args[0] for call in session.add.call_args_list]
    alias = next(item for item in added if isinstance(item, ScopeReferenceAlias))
    event = next(item for item in added if isinstance(item, AuditEvent))
    assert alias.id == alias_id
    assert alias.normalized_ref == "during testing"
    assert event.event_type == "scope_alias.recorded"
    assert event.actor_role == "compliance_admin"
    session.commit.assert_awaited_once()


def test_deadline_rederivation_is_noop_until_state_changes() -> None:
    deadline = Deadline(
        id=UUID("33333333-3333-4333-8333-333333333331"),
        rule_id="annual-review",
        citation="34 CFR §300.324(b)(1)(i)",
        student_ref="RIV-204",
        iep_record_version_id=UUID("11111111-1111-4111-8111-111111111111"),
        source_kind=SourceKind.IEP_RECORD,
        source_ref=UUID("11111111-1111-4111-8111-111111111111"),
        legal_due_on=date(2026, 7, 21),
        action_due_on=date(2026, 7, 21),
        warning_30_on=date(2026, 6, 19),
        warning_14_on=date(2026, 7, 7),
        warning_3_on=date(2026, 7, 17),
        status=DeadlineStatus.UPCOMING,
        description="Complete the annual IEP review.",
    )
    row = ComplianceDeadline(
        id=deadline.id,
        iep_record_version_id=deadline.iep_record_version_id,
        student_ref=deadline.student_ref,
        rule_id=deadline.rule_id,
        citation=deadline.citation,
        source_kind=deadline.source_kind.value,
        source_ref=deadline.source_ref,
        legal_due_on=deadline.legal_due_on,
        action_due_on=deadline.action_due_on,
        warning_30_on=deadline.warning_30_on,
        warning_14_on=deadline.warning_14_on,
        warning_3_on=deadline.warning_3_on,
        status="upcoming",
        description=deadline.description,
    )
    occurred_at = datetime(2026, 7, 20, 3, tzinfo=UTC)

    assert _sync_deadline(row, deadline, occurred_at) is None

    overdue = deadline.model_copy(update={"status": DeadlineStatus.OVERDUE})
    event = _sync_deadline(row, overdue, occurred_at)
    assert event is not None
    assert event.event_type == "deadline.recalculated"
    assert row.status == "overdue"
