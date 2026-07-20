"""Immutable registry of cited deterministic rules."""

from __future__ import annotations

from typing import Protocol

from bridgeline.rules.families.deadlines import (
    AnnualReviewRule,
    InitialIEPMeetingRule,
    ProgressReportCadenceRule,
    TriennialReevaluationRule,
)
from bridgeline.rules.families.distribution import (
    TeacherAccessRule,
    TeacherAccommodationsRule,
    TeacherResponsibilitiesRule,
)
from bridgeline.rules.families.gaps import IEPInEffectRule, ServicesWithoutDelayRule
from bridgeline.rules.families.minutes import ServicesStatementRule
from bridgeline.rules.types import (
    ApprovedRecord,
    Deadline,
    DerivedObligation,
    Finding,
    RosterSnapshot,
    RuleState,
)

RULES_VERSION = "2026.07.20.5"


class Rule(Protocol):
    """Interface implemented by every independently testable rule."""

    id: str
    citation: str
    description: str

    def derive(
        self, record: ApprovedRecord, roster: RosterSnapshot
    ) -> tuple[DerivedObligation, ...]: ...

    def check(self, state: RuleState) -> tuple[Finding, ...]: ...

    def derive_deadlines(
        self, record: ApprovedRecord, roster: RosterSnapshot
    ) -> tuple[Deadline, ...]: ...


def _build_registry(*rules: Rule) -> tuple[Rule, ...]:
    ids = [rule.id for rule in rules]
    if len(ids) != len(set(ids)):
        raise ValueError("rule IDs must be unique")
    return rules


RULES: tuple[Rule, ...] = _build_registry(
    TeacherAccessRule(),
    TeacherResponsibilitiesRule(),
    TeacherAccommodationsRule(),
    InitialIEPMeetingRule(),
    AnnualReviewRule(),
    TriennialReevaluationRule(),
    ProgressReportCadenceRule(),
    ServicesStatementRule(),
    ServicesWithoutDelayRule(),
    IEPInEffectRule(),
)
RULES_BY_ID: dict[str, Rule] = {rule.id: rule for rule in RULES}
