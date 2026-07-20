"""Deterministic resolution of document-stated accommodation scopes."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from bridgeline.db.schemas import (
    Accommodation,
    AccommodationScope,
    AccommodationScopeReference,
)
from bridgeline.rules.types import (
    RosterClass,
    RosterSnapshot,
    ScopeMappingKind,
    ScopeProvenance,
)


@dataclass(frozen=True, slots=True)
class ScopeResolutionIssue:
    """One scope reference that cannot be mapped without guessing."""

    finding_type: str
    reference: AccommodationScopeReference
    detail: str


@dataclass(frozen=True, slots=True)
class ResolvedClassScope:
    """One applicable class and the exact references that selected it."""

    classroom: RosterClass
    provenance: tuple[ScopeProvenance, ...]


@dataclass(frozen=True, slots=True)
class ScopeResolution:
    """Complete deterministic result for one accommodation."""

    classes: tuple[ResolvedClassScope, ...]
    issues: tuple[ScopeResolutionIssue, ...]


def normalize_scope_text(value: str) -> str:
    """Normalize only for matching while preserving the approved source value."""

    normalized = unicodedata.normalize("NFKC", value)
    return re.sub(r"\s+", " ", normalized).strip().casefold()


def resolve_scope(accommodation: Accommodation, roster: RosterSnapshot) -> ScopeResolution:
    """Resolve union-within-scope and intersection-across-scope applicability."""

    references = tuple(accommodation.applies_to_refs)
    if references[0].scope is AccommodationScope.ALL:
        provenance = (_provenance(references[0]),)
        return ScopeResolution(
            classes=tuple(
                ResolvedClassScope(classroom=classroom, provenance=provenance)
                for classroom in roster.classes
            ),
            issues=(),
        )

    subject_refs = tuple(
        reference for reference in references if reference.scope is AccommodationScope.SUBJECT
    )
    context_refs = tuple(
        reference for reference in references if reference.scope is AccommodationScope.CONTEXT
    )
    subject_classes: dict[str, tuple[RosterClass, tuple[AccommodationScopeReference, ...]]] = {}
    issues: list[ScopeResolutionIssue] = []

    for reference in subject_refs:
        matches, issue = _resolve_subject(reference, roster, accommodation.id)
        if issue is not None:
            issues.append(issue)
            continue
        for classroom in matches:
            existing = subject_classes.get(classroom.class_ref)
            matched_refs = () if existing is None else existing[1]
            subject_classes[classroom.class_ref] = (classroom, (*matched_refs, reference))

    for reference in context_refs:
        issue = _resolve_context(reference, roster, accommodation.id)
        if issue is not None:
            issues.append(issue)

    if issues:
        return ScopeResolution(classes=(), issues=tuple(issues))

    candidates = (
        tuple(value for _, value in sorted(subject_classes.items()))
        if subject_refs
        else tuple((classroom, ()) for classroom in roster.classes)
    )
    return ScopeResolution(
        classes=tuple(
            ResolvedClassScope(
                classroom=classroom,
                provenance=tuple(
                    sorted(
                        (
                            *(_provenance(reference) for reference in matched_subject_refs),
                            *(_provenance(reference) for reference in context_refs),
                        ),
                        key=_provenance_key,
                    )
                ),
            )
            for classroom, matched_subject_refs in candidates
        ),
        issues=(),
    )


def _resolve_subject(
    reference: AccommodationScopeReference,
    roster: RosterSnapshot,
    accommodation_id: object,
) -> tuple[tuple[RosterClass, ...], ScopeResolutionIssue | None]:
    targets = _mapped_targets(
        reference, roster, ScopeMappingKind.HUMAN_RESOLUTION, accommodation_id
    )
    if not targets:
        exact = tuple(
            classroom
            for classroom in roster.classes
            if normalize_scope_text(classroom.subject) == normalize_scope_text(reference.ref)
        )
        if exact:
            return _one_class_or_issue(reference, exact)
        targets = _mapped_targets(
            reference, roster, ScopeMappingKind.DISTRICT_ALIAS, accommodation_id
        )
    matches = tuple(
        classroom
        for classroom in roster.classes
        if normalize_scope_text(classroom.subject) in targets
    )
    if not matches:
        return (), _unresolved(reference)
    return _one_class_or_issue(reference, matches)


def _resolve_context(
    reference: AccommodationScopeReference,
    roster: RosterSnapshot,
    accommodation_id: object,
) -> ScopeResolutionIssue | None:
    human_targets = _mapped_targets(
        reference, roster, ScopeMappingKind.HUMAN_RESOLUTION, accommodation_id
    )
    targets = human_targets or _mapped_targets(
        reference, roster, ScopeMappingKind.DISTRICT_ALIAS, accommodation_id
    )
    if not targets:
        return _unresolved(reference)
    if len(targets) > 1:
        return _ambiguous(reference, len(targets))
    return None


def _mapped_targets(
    reference: AccommodationScopeReference,
    roster: RosterSnapshot,
    kind: ScopeMappingKind,
    accommodation_id: object,
) -> set[str]:
    source_key = normalize_scope_text(reference.ref)
    return {
        normalize_scope_text(mapping.target_ref)
        for mapping in roster.scope_mappings
        if mapping.kind is kind
        and (mapping.accommodation_id is None or mapping.accommodation_id == accommodation_id)
        and mapping.scope is reference.scope
        and normalize_scope_text(mapping.document_ref) == source_key
    }


def _one_class_or_issue(
    reference: AccommodationScopeReference,
    matches: tuple[RosterClass, ...],
) -> tuple[tuple[RosterClass, ...], ScopeResolutionIssue | None]:
    if len(matches) > 1:
        return (), _ambiguous(reference, len(matches))
    return matches, None


def _unresolved(reference: AccommodationScopeReference) -> ScopeResolutionIssue:
    return ScopeResolutionIssue(
        finding_type="scope-reference-unresolved",
        reference=reference,
        detail=f'Scope reference "{reference.ref}" does not match the active roster.',
    )


def _ambiguous(reference: AccommodationScopeReference, match_count: int) -> ScopeResolutionIssue:
    return ScopeResolutionIssue(
        finding_type="scope-reference-ambiguous",
        reference=reference,
        detail=(
            f'Scope reference "{reference.ref}" matches {match_count} roster targets; '
            "a case manager must select one."
        ),
    )


def _provenance(reference: AccommodationScopeReference) -> ScopeProvenance:
    return ScopeProvenance(
        scope=reference.scope,
        ref=reference.ref,
        source_page=reference.source_page,
        source_quote=reference.source_quote,
        confidence=reference.confidence,
    )


def _provenance_key(item: ScopeProvenance) -> tuple[str, str, int, str]:
    return (
        item.scope.value,
        normalize_scope_text(item.ref),
        item.source_page,
        item.source_quote,
    )
