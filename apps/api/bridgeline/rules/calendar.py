"""School-local date arithmetic for compliance deadlines."""

from __future__ import annotations

import calendar as month_calendar
import re
from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum

from bridgeline.rules.types import CalendarDay, DeadlineStatus, SchoolTerm, TermKind


class CalendarCoverageError(ValueError):
    """The district calendar cannot resolve a required action date."""


class UnsupportedCadenceError(ValueError):
    """A progress cadence falls outside the deterministic finite grammar."""


class CadenceKind(StrEnum):
    """Supported deterministic progress cadence operations."""

    DAYS = "days"
    MONTHS = "months"
    GRADING_PERIOD = "grading_period"


@dataclass(frozen=True, slots=True)
class ParsedCadence:
    """Normalized cadence operation without free-text ambiguity."""

    kind: CadenceKind
    amount: int


_NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
}


def previous_instructional_day(target: date, days: tuple[CalendarDay, ...]) -> date:
    """Return target or the closest earlier instructional date in supplied coverage."""

    instructional = {item.day for item in days if item.instructional}
    covered = {item.day for item in days}
    candidate = target
    while candidate in covered:
        if candidate in instructional:
            return candidate
        candidate -= timedelta(days=1)
    raise CalendarCoverageError(f"calendar does not cover {target.isoformat()} or an earlier day")


def warning_date(legal_due_on: date, lead_days: int, days: tuple[CalendarDay, ...]) -> date:
    """Subtract calendar days, then move action to the previous instructional date."""

    return previous_instructional_day(legal_due_on - timedelta(days=lead_days), days)


def deadline_status(legal_due_on: date, as_of: date) -> DeadlineStatus:
    """Classify a deadline without converting either school-local date."""

    if as_of > legal_due_on:
        return DeadlineStatus.OVERDUE
    if as_of == legal_due_on:
        return DeadlineStatus.DUE
    return DeadlineStatus.UPCOMING


def parse_progress_cadence(value: str) -> ParsedCadence:
    """Parse only the approved finite cadence grammar."""

    normalized = " ".join(value.casefold().strip().split())
    fixed = {
        "weekly": ParsedCadence(CadenceKind.DAYS, 7),
        "monthly": ParsedCadence(CadenceKind.MONTHS, 1),
        "quarterly": ParsedCadence(CadenceKind.MONTHS, 3),
        "each grading period": ParsedCadence(CadenceKind.GRADING_PERIOD, 1),
        "every grading period": ParsedCadence(CadenceKind.GRADING_PERIOD, 1),
    }
    if normalized in fixed:
        return fixed[normalized]
    match = re.fullmatch(r"every ([a-z]+|\d+) weeks?", normalized)
    if match is not None:
        token = match.group(1)
        amount = int(token) if token.isdigit() else _NUMBER_WORDS.get(token)
        if amount is not None and 1 <= amount <= 52:
            return ParsedCadence(CadenceKind.DAYS, amount * 7)
    raise UnsupportedCadenceError(f"unsupported progress cadence: {value!r}")


def next_cadence_date(
    last_report_on: date,
    cadence: ParsedCadence,
    terms: tuple[SchoolTerm, ...],
) -> date:
    """Calculate the next legal report date from normalized cadence."""

    if cadence.kind is CadenceKind.DAYS:
        return last_report_on + timedelta(days=cadence.amount)
    if cadence.kind is CadenceKind.MONTHS:
        return add_months(last_report_on, cadence.amount)
    grading_period_ends = sorted(
        term.end_on
        for term in terms
        if term.kind is TermKind.GRADING_PERIOD and term.end_on > last_report_on
    )
    if not grading_period_ends:
        raise CalendarCoverageError("calendar has no later grading-period end")
    return grading_period_ends[0]


def add_months(value: date, months: int) -> date:
    """Add whole calendar months and clamp to the destination month's final day."""

    absolute_month = value.year * 12 + value.month - 1 + months
    year, zero_based_month = divmod(absolute_month, 12)
    month = zero_based_month + 1
    day = min(value.day, month_calendar.monthrange(year, month)[1])
    return date(year, month, day)
