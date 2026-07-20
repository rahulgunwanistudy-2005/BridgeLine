"""Deterministic computation of the three scripted findings from the engineered data.

This is the acceptance gate for STEP 2: it recomputes each finding from the same builder
output that gets written to disk and asserts the exact demo numbers. If any finding stops
firing, verification fails loudly rather than the demo failing on camera.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from synthgen.progress import (
    BELL,
    BELL_MANDATE_PER_SESSION,
    BELL_SERVICE_KEY,
    BELL_SESSIONS_PER_WEEK,
    SHARMA,
    SHARMA_CONFIRMED_CLASSES,
    SHARMA_GOAL2_KEY,
    build_confirmations,
    build_gradebook,
    build_service_logs,
    build_teacher_notes,
    _goal_id,
)


@dataclass
class Finding:
    key: str
    title: str
    fired: bool
    detail: str
    evidence: dict[str, Any] = field(default_factory=dict)


def _finding_a() -> Finding:
    """Conflict: ~40% comprehension mastery vs a 'doing well' teacher note (Goal 2)."""

    gradebook, _ = build_gradebook()
    goal2_id = _goal_id(SHARMA, SHARMA_GOAL2_KEY)
    percents = [
        r["percent"]
        for rows in gradebook.values()
        for r in rows
        if r["student_ref"] == SHARMA and r["iep_goal_id"] == goal2_id
    ]
    avg = sum(percents) / len(percents) if percents else None

    notes = build_teacher_notes()
    positive = next(
        (n for n in notes
         if n["student_ref"] == SHARMA and n["iep_goal_key"] == SHARMA_GOAL2_KEY
         and "doing well" in n["text"].lower()),
        None,
    )
    fired = bool(percents) and avg is not None and avg <= 50 and positive is not None
    detail = (
        f"A. Sharma, Goal 2: gradebook shows {avg:.0f}% mastery across {len(percents)} "
        f"comprehension assessments, but Ms. Delgado's check-in says \"doing well\" — flag for meeting."
        if fired else "conflict did not fire"
    )
    return Finding("a_goal_conflict", "Goal-2 progress conflict", fired, detail,
                   {"avg_percent": avg, "n_assessments": len(percents),
                    "note_id": positive["note_id"] if positive else None})


def _finding_b() -> Finding:
    """Implementation gap: extended-time confirmed in only 3 of 6 classes."""

    confirmations = build_confirmations()
    sharma = [c for c in confirmations
              if c["student_ref"] == SHARMA and c["accommodation_key"] == "extended-time"]
    total = len(sharma)
    confirmed = [c for c in sharma if c["confirmed"] == "true"]
    unconfirmed = [c["class_ref"] for c in sharma if c["confirmed"] != "true"]
    fired = total == 6 and len(confirmed) == 3 and sorted(
        c["class_ref"] for c in confirmed) == sorted(SHARMA_CONFIRMED_CLASSES)
    detail = (
        f"A. Sharma's extended-time accommodation is confirmed in only {len(confirmed)} of "
        f"{total} classes — dropped in {', '.join(unconfirmed)}."
        if fired else "gap did not fire"
    )
    return Finding("b_implementation_gap", "Extended-time 3-of-6 gap", fired, detail,
                   {"confirmed": len(confirmed), "total": total, "unconfirmed": unconfirmed})


def _finding_c() -> Finding:
    """Minute variance: SAI delivered 20 min/wk under mandate."""

    logs = build_service_logs()
    rows = [r for r in logs.get(BELL, []) if r["service_key"] == BELL_SERVICE_KEY]
    if not rows:
        return Finding("c_minute_variance", "Service minute variance", False,
                       "no service log rows", {})
    avg_delivered = sum(r["minutes_delivered"] for r in rows) / len(rows)
    variance_per_week = round((avg_delivered - BELL_MANDATE_PER_SESSION) * BELL_SESSIONS_PER_WEEK)
    mandate_per_week = BELL_MANDATE_PER_SESSION * BELL_SESSIONS_PER_WEEK
    delivered_per_week = round(avg_delivered * BELL_SESSIONS_PER_WEEK)
    fired = variance_per_week == -20
    detail = (
        f"M. Bell, Specialized academic instruction: {delivered_per_week} min/wk delivered "
        f"against a {mandate_per_week} min/wk mandate — {variance_per_week} min/wk under."
        if fired else f"variance was {variance_per_week}, expected -20"
    )
    return Finding("c_minute_variance", "Service minute variance", fired, detail,
                   {"delivered_per_week": delivered_per_week, "mandate_per_week": mandate_per_week,
                    "variance_per_week": variance_per_week, "sessions_logged": len(rows)})


def compute_findings() -> list[Finding]:
    return [_finding_a(), _finding_b(), _finding_c()]
