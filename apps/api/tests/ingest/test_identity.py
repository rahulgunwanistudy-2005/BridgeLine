"""Tests for deterministic stable-ID reconciliation."""

import ast
from pathlib import Path
from uuid import UUID

from bridgeline.db.schemas import (
    AccommodationScope,
    AccommodationScopeReference,
    ReconciliationStatus,
)
from bridgeline.ingest import identity as identity_module
from bridgeline.ingest.identity import reconcile_identities

from .conftest import sample_record


def test_identity_module_has_no_llm_import_boundary() -> None:
    """Keep deterministic reconciliation structurally unable to reach an LLM gateway."""

    assert identity_module.__file__ is not None
    tree = ast.parse(Path(identity_module.__file__).read_text(encoding="utf-8"))
    imported_modules = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_modules.update(
        node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
    )

    assert not any(module.startswith("bridgeline.llm") for module in imported_modules)


def test_first_extraction_allocates_ids_and_null_statuses() -> None:
    """New lineages receive system IDs without pretending a comparison occurred."""

    draft = sample_record().model_copy(deep=True)
    draft.accommodations[0].id = UUID(int=0)

    reconciled = reconcile_identities(draft, prior=None)

    assert reconciled.accommodations[0].id != UUID(int=0)
    assert reconciled.accommodations[0].reconciliation_status is None


def test_unique_exact_content_and_anchor_preserve_prior_id() -> None:
    """A unique source-grounded match carries stable identity forward."""

    prior = sample_record()
    draft = sample_record().model_copy(deep=True)
    draft.accommodations[0].id = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")

    reconciled = reconcile_identities(draft, prior=prior)

    assert reconciled.accommodations[0].id == prior.accommodations[0].id
    assert reconciled.accommodations[0].reconciliation_status is ReconciliationStatus.MATCHED


def test_multiple_credible_duplicate_matches_are_ambiguous() -> None:
    """Duplicate prior wording never causes an arbitrary legal-history carry-forward."""

    prior = sample_record().model_copy(deep=True)
    duplicate = prior.accommodations[0].model_copy(
        update={"id": UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")}
    )
    prior.accommodations.append(duplicate)
    draft = sample_record().model_copy(deep=True)
    provisional = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    draft.accommodations[0].id = provisional

    reconciled = reconcile_identities(draft, prior=prior)

    assert reconciled.accommodations[0].id == provisional
    assert reconciled.accommodations[0].reconciliation_status is ReconciliationStatus.AMBIGUOUS


def test_scope_change_on_same_content_and_anchor_requires_review() -> None:
    """A teacher-affecting scope change cannot silently inherit the prior identity."""

    prior = sample_record()
    draft = sample_record().model_copy(deep=True)
    provisional = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    draft.accommodations[0].id = provisional
    draft.accommodations[0].applies_to_refs = [
        AccommodationScopeReference(
            scope=AccommodationScope.SUBJECT,
            ref="Mathematics",
            source_page=5,
            source_quote="in Mathematics",
            confidence=0.98,
        )
    ]

    reconciled = reconcile_identities(draft, prior=prior)

    assert reconciled.accommodations[0].id == provisional
    assert reconciled.accommodations[0].reconciliation_status is ReconciliationStatus.AMBIGUOUS


def test_same_text_clauses_match_their_distinct_scope_fingerprints() -> None:
    """Two disjunctive clauses carry the correct prior IDs independently."""

    prior = sample_record().model_copy(deep=True)
    subject_clause = prior.accommodations[0].model_copy(
        update={
            "id": UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"),
            "applies_to_refs": [
                AccommodationScopeReference(
                    scope=AccommodationScope.SUBJECT,
                    ref="Mathematics",
                    source_page=5,
                    source_quote="in Mathematics",
                    confidence=0.98,
                )
            ],
        }
    )
    prior.accommodations.append(subject_clause)
    draft = prior.model_copy(deep=True)
    for accommodation in draft.accommodations:
        accommodation.id = UUID(int=0)

    reconciled = reconcile_identities(draft, prior=prior)

    assert [item.id for item in reconciled.accommodations] == [
        item.id for item in prior.accommodations
    ]
    assert all(
        item.reconciliation_status is ReconciliationStatus.MATCHED
        for item in reconciled.accommodations
    )
