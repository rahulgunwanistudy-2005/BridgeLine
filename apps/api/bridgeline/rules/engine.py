"""Canonical deterministic driver for the registered rules."""

from __future__ import annotations

from bridgeline.rules.families.gaps import IEPInEffectRule
from bridgeline.rules.registry import RULES, RULES_BY_ID, RULES_VERSION, Rule
from bridgeline.rules.types import (
    ApprovedRecord,
    Deadline,
    DerivationResult,
    DerivedObligation,
    DistrictRuleState,
    Finding,
    RosterSnapshot,
    RuleState,
    SourceKind,
)


class RuleInvariantError(ValueError):
    """A registered rule emitted an internally inconsistent result."""


class UnmatchedAccommodationScopeError(RuleInvariantError):
    """An approved scoped accommodation does not match any enrolled class."""


def derive_district_findings(state: DistrictRuleState) -> tuple[Finding, ...]:
    """Run baseline district checks without requiring an approved IEP version."""

    findings = IEPInEffectRule().check_district(state)
    _validate_findings(findings)
    return tuple(sorted(findings, key=lambda item: str(item.id)))


def derive_obligations(
    approved: ApprovedRecord,
    roster: RosterSnapshot,
    *,
    rules: tuple[Rule, ...] = RULES,
) -> DerivationResult:
    """Run rules and return validated outputs in canonical byte-stable order."""

    obligations = tuple(item for rule in rules for item in rule.derive(approved, roster))
    deadlines = tuple(item for rule in rules for item in rule.derive_deadlines(approved, roster))
    state = RuleState(approved=approved, roster=roster)
    findings = tuple(item for rule in rules for item in rule.check(state))
    _validate_obligations(approved, roster, obligations, findings)
    _validate_findings(findings)
    _validate_deadlines(deadlines)
    return DerivationResult(
        generated_at=roster.generated_at,
        rules_version=RULES_VERSION,
        obligations=tuple(sorted(obligations, key=_obligation_key)),
        deadlines=tuple(sorted(deadlines, key=lambda item: str(item.id))),
        findings=tuple(sorted(findings, key=lambda item: str(item.id))),
    )


def _validate_obligations(
    approved: ApprovedRecord,
    roster: RosterSnapshot,
    obligations: tuple[DerivedObligation, ...],
    findings: tuple[Finding, ...],
) -> None:
    ids = [item.id for item in obligations]
    if len(ids) != len(set(ids)):
        raise RuleInvariantError("derivation emitted duplicate obligation IDs")
    for item in obligations:
        registered = RULES_BY_ID.get(item.rule_id)
        if registered is None or registered.citation != item.citation:
            raise RuleInvariantError(f"obligation {item.id} has unregistered rule provenance")
        if item.source_kind is SourceKind.IEP_RECORD and item.source_ref != approved.row_id:
            raise RuleInvariantError(f"obligation {item.id} points to the wrong IEP version")
        if item.source_kind is SourceKind.ACCOMMODATION:
            source = next(
                (
                    accommodation
                    for accommodation in approved.record.accommodations
                    if accommodation.id == item.source_ref
                ),
                None,
            )
            if source is None or not item.scope_provenance:
                raise RuleInvariantError(
                    f"obligation {item.id} lacks accommodation scope provenance"
                )
            approved_evidence = {
                (
                    reference.scope.value,
                    reference.ref,
                    reference.source_page,
                    reference.source_quote,
                    reference.confidence,
                )
                for reference in source.applies_to_refs
            }
            emitted_evidence = {
                (
                    evidence.scope.value,
                    evidence.ref,
                    evidence.source_page,
                    evidence.source_quote,
                    evidence.confidence,
                )
                for evidence in item.scope_provenance
            }
            if not emitted_evidence.issubset(approved_evidence):
                raise RuleInvariantError(f"obligation {item.id} has unapproved scope provenance")
        elif item.scope_provenance:
            raise RuleInvariantError(
                f"obligation {item.id} has scope provenance without an accommodation source"
            )
    if roster.classes:
        emitted_accommodations = {
            item.source_ref for item in obligations if item.source_kind is SourceKind.ACCOMMODATION
        }
        review_accommodations = {
            str(item.related_refs.get("accommodation_id"))
            for item in findings
            if item.finding_type in {"scope-reference-unresolved", "scope-reference-ambiguous"}
        }
        missing = [
            accommodation.id
            for accommodation in approved.record.accommodations
            if accommodation.id not in emitted_accommodations
            and str(accommodation.id) not in review_accommodations
        ]
        if missing:
            raise UnmatchedAccommodationScopeError(
                "scoped accommodations match no enrolled class: "
                + ", ".join(str(value) for value in missing)
            )


def _validate_findings(findings: tuple[Finding, ...]) -> None:
    ids = [item.id for item in findings]
    if len(ids) != len(set(ids)):
        raise RuleInvariantError("checks emitted duplicate finding IDs")
    for item in findings:
        registered = RULES_BY_ID.get(item.rule_id)
        if registered is None or registered.citation != item.citation:
            raise RuleInvariantError(f"finding {item.id} has unregistered rule provenance")


def _validate_deadlines(deadlines: tuple[Deadline, ...]) -> None:
    ids = [item.id for item in deadlines]
    if len(ids) != len(set(ids)):
        raise RuleInvariantError("derivation emitted duplicate deadline IDs")
    for item in deadlines:
        registered = RULES_BY_ID.get(item.rule_id)
        if registered is None or registered.citation != item.citation:
            raise RuleInvariantError(f"deadline {item.id} has unregistered rule provenance")


def _obligation_key(item: DerivedObligation) -> tuple[str, ...]:
    return (
        item.assignee_kind.value,
        item.assignee_ref,
        item.context_kind.value,
        item.context_ref,
        item.rule_id,
        item.source_kind.value,
        str(item.source_ref),
    )
