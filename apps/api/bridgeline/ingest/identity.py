"""Deterministic stable-ID reconciliation for extracted IEP items."""

from __future__ import annotations

import re
from collections.abc import Callable
from uuid import uuid4

from bridgeline.db.schemas import (
    Accommodation,
    Goal,
    IEPRecord,
    ReconciliationStatus,
    Service,
)


def reconcile_identities(draft: IEPRecord, prior: IEPRecord | None) -> IEPRecord:
    """Return a copied record with stable item IDs and explicit match statuses."""

    result = draft.model_copy(deep=True)
    if prior is None:
        _assign_first_extraction(result.accommodations)
        _assign_first_extraction(result.services)
        _assign_first_extraction(result.goals)
        return result

    result.accommodations = _reconcile(
        result.accommodations, prior.accommodations, _accommodation_signature
    )
    result.services = _reconcile(result.services, prior.services, _service_signature)
    result.goals = _reconcile(result.goals, prior.goals, _goal_signature)
    return result


def _assign_first_extraction[Item: Accommodation | Service | Goal](items: list[Item]) -> None:
    for item in items:
        if item.id.int == 0:
            item.id = uuid4()
        item.reconciliation_status = None


def _reconcile[Item: Accommodation | Service | Goal](
    current: list[Item],
    previous: list[Item],
    signature: Callable[[Item], tuple[object, ...]],
) -> list[Item]:
    by_signature: dict[tuple[object, ...], list[Item]] = {}
    for item in previous:
        by_signature.setdefault(signature(item), []).append(item)

    for item in current:
        matches = by_signature.get(signature(item), [])
        if len(matches) == 1:
            item.id = matches[0].id
            item.reconciliation_status = ReconciliationStatus.MATCHED
        elif len(matches) > 1:
            if item.id.int == 0:
                item.id = uuid4()
            item.reconciliation_status = ReconciliationStatus.AMBIGUOUS
        else:
            if item.id.int == 0:
                item.id = uuid4()
            item.reconciliation_status = ReconciliationStatus.NEW
    return current


def _anchor(item: Accommodation | Service | Goal) -> tuple[int, str]:
    return item.source_page, _text(item.source_quote)


def _accommodation_signature(item: Accommodation) -> tuple[object, ...]:
    return (
        _text(item.text),
        tuple(sorted(scope.value for scope in item.applies_to)),
        *_anchor(item),
    )


def _service_signature(item: Service) -> tuple[object, ...]:
    return (
        _text(item.type),
        item.minutes_per_week,
        _text(item.frequency),
        _text(item.provider_role),
        item.start,
        item.end,
        *_anchor(item),
    )


def _goal_signature(item: Goal) -> tuple[object, ...]:
    return (
        _text(item.text),
        _text(item.baseline),
        _text(item.target),
        _text(item.measure),
        _text(item.progress_cadence),
        *_anchor(item),
    )


def _text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()
