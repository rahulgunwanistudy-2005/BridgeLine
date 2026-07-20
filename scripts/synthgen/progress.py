"""Engineered progress history: gradebooks, service logs, teacher notes, confirmations.

Constructed so exactly three findings fire deterministically against the ground truth:

  (a) RIV-1001 A. Sharma, Goal 2 (comprehension): gradebook mastery ~40% while a teacher
      check-in says "doing well" — a reconciliation conflict.
  (b) RIV-1001 extended-time accommodation confirmed in only 3 of 6 classes — an
      implementation gap (rules-engine Family-4 test case).
  (c) RIV-1002 M. Bell, Specialized academic instruction: delivered 130 min/wk against a
      150 min/wk mandate — 20 min/wk under (minute-variance).

Plus deliberate noise: unmappable gradebook signals, malformed CSV rows for the
quarantine path, and clean students with no findings so the dashboard is not all red.

An `iep_goal_key`/`iep_goal_id` annotation column carries the ground-truth signal→goal
mapping so findings are deterministic; realistic assignment names remain for the
reconciler's own NLP mapping to work on.
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from typing import Any

from synthgen.constants import RANDOM_SEED, stable_uuid
from synthgen.district import CLASSES, CORE_CLASS_REFS, build_district
from synthgen.ground_truth import build_records

# Engineered targets — the exact numbers the three findings depend on.
SHARMA = "RIV-1001"
SHARMA_GOAL2_KEY = "g2-comprehension"
SHARMA_GOAL2_PERCENTS = [42, 38, 40, 41, 39]  # avg 40.0 — "~40% mastery"
SHARMA_EXTENDED_TIME_KEY = "extended-time"
SHARMA_CONFIRMED_CLASSES = ["ENG-101", "MTH-101", "BIO-101"]      # 3 of 6 confirmed
SHARMA_UNCONFIRMED_CLASSES = ["HIS-101", "PE-101", "ART-101"]      # 3 of 6 dropped

BELL = "RIV-1002"
BELL_SERVICE_KEY = "sai-support"
BELL_MANDATE_PER_SESSION = 30
BELL_DELIVERED_PER_SESSION = 26   # 5 sessions/wk × (30-26) = 20 min/wk short
BELL_SESSIONS_PER_WEEK = 5

# Metric labels mirror ProgressSignal.Measurement.metric examples.
METRIC_PCT = "assignment_percentage"
METRIC_MINUTES = "minutes_delivered"
METRIC_NARRATIVE = "teacher_narrative"


def _goal_id(student_ref: str, goal_key: str) -> str:
    return stable_uuid("goal", student_ref, goal_key)


def _instructional_days() -> list[date]:
    cal = build_district()["calendar"]
    return [date.fromisoformat(d) for d in cal["instructional_days"]]


def _biweekly_assessment_days() -> list[date]:
    """Every other Wednesday that is an instructional day — the assessment cadence."""

    days = _instructional_days()
    day_set = set(days)
    wednesdays = [d for d in days if d.weekday() == 2]
    picked: list[date] = []
    for i, wed in enumerate(wednesdays):
        if i % 2 == 0 and wed in day_set:
            picked.append(wed)
    return picked


def _weeks() -> list[list[date]]:
    """Group instructional days into Monday-anchored weeks."""

    days = _instructional_days()
    weeks: dict[date, list[date]] = {}
    for d in days:
        monday = d - timedelta(days=d.weekday())
        weeks.setdefault(monday, []).append(d)
    return [weeks[m] for m in sorted(weeks)]


# ── Gradebook ────────────────────────────────────────────────────────────────
GRADEBOOK_COLUMNS = [
    "row_id", "date", "student_ref", "class_ref", "assignment", "category",
    "percent", "iep_goal_key", "iep_goal_id",
]

# Which class carries each IEP student's goal-linked coursework (subject alignment).
_GOAL_CLASS = {
    "ENG-101": ("reading", "writing", "comprehension", "fluency", "vocabulary", "narrative", "grammar"),
    "MTH-101": ("computation", "equations", "math"),
}


def _student_baseline(student_ref: str) -> int:
    rng = random.Random(f"{RANDOM_SEED}:{student_ref}:baseline")
    return rng.randint(74, 89)


# Authored goal keys per student (must mirror the keys used in ground_truth.py). Used to
# recover a goal's authored key from its deterministic UUID for signal→goal annotation.
_GOAL_KEYS: dict[str, list[str]] = {
    "RIV-1001": ["g1-decoding", "g2-comprehension", "g3-writing"],
    "RIV-1002": ["g1-initiation", "g2-peer"],
    "RIV-1003": ["g1-articulation", "g2-narrative"],
    "RIV-1004": ["g1-task-completion", "g2-materials"],
    "RIV-1005": ["g1-selfadvocacy", "g2-vocabulary"],
    "RIV-1006": ["g1-computation", "g2-writtenexpression"],
    "RIV-1007": ["g1-flexibility", "g2-writing"],
    "RIV-1008": ["g1-focus", "g2-selfmonitor"],
    "RIV-1009": ["g1-grammar", "g2-following-directions"],
    "RIV-1010": ["g1-fluency", "g2-comprehension", "g3-writing"],
    "RIV-1011": ["g1-vocabulary", "g2-selfadvocacy"],
    "RIV-1012": ["g1-conversation", "g2-organization"],
}


def _goal_for_assignment(
    student_ref: str, class_ref: str, records_by_ref: dict[str, Any]
) -> tuple[str, str] | None:
    """Pick a goal to tag a class's assignment with, by subject keyword overlap."""

    record = records_by_ref.get(student_ref)
    keywords = _GOAL_CLASS.get(class_ref)
    if not record or not keywords:
        return None
    goals_by_id = {g["id"]: g for g in record["goals"]}
    for key in _GOAL_KEYS.get(student_ref, []):
        gid = _goal_id(student_ref, key)
        goal = goals_by_id.get(gid)
        if goal and any(k in key or k in goal["text"].lower() for k in keywords):
            return key, gid
    return None


def build_gradebook() -> tuple[dict[str, list[dict[str, Any]]], list[tuple[str, str]]]:
    """Return {class_ref: [rows]} plus malformed raw lines to append for quarantine.

    Malformed lines are returned as (class_ref, raw_csv_line) pairs.
    """

    records_by_ref = {r["student_ref"]: r for r, _ in build_records()}
    district = build_district()
    enrolled: dict[str, list[str]] = {c: [] for c in CORE_CLASS_REFS}
    for e in district["enrollments"]:
        enrolled[e["class_ref"]].append(e["student_ref"])

    assessment_days = _biweekly_assessment_days()
    gradebook: dict[str, list[dict[str, Any]]] = {c: [] for c in CORE_CLASS_REFS}
    counter = 0

    for class_ref in CORE_CLASS_REFS:
        subject = next(c["subject_ref"] for c in CLASSES if c["class_ref"] == class_ref)
        for a_idx, day in enumerate(assessment_days):
            assignment = f"{subject} Assessment {a_idx + 1}"
            for student_ref in sorted(enrolled[class_ref]):
                # Skip assessments before a student's enrollment start (mid-sem enrollee).
                start = next(e["start"] for e in district["enrollments"]
                             if e["student_ref"] == student_ref and e["class_ref"] == class_ref)
                if day.isoformat() < start:
                    continue
                counter += 1
                row_id = f"GB-{counter:05d}"
                goal_link = _goal_for_assignment(student_ref, class_ref, records_by_ref)
                percent, category, goal_key, goal_id = _score_for(
                    student_ref, class_ref, a_idx, goal_link
                )
                gradebook[class_ref].append({
                    "row_id": row_id,
                    "date": day.isoformat(),
                    "student_ref": student_ref,
                    "class_ref": class_ref,
                    "assignment": assignment,
                    "category": category,
                    "percent": percent,
                    "iep_goal_key": goal_key,
                    "iep_goal_id": goal_id,
                })

    # A couple of unmappable signals: participation rows with no goal linkage.
    counter += 1
    gradebook["PE-101"].append({
        "row_id": f"GB-{counter:05d}", "date": assessment_days[1].isoformat(),
        "student_ref": "RIV-1012", "class_ref": "PE-101",
        "assignment": "Class Participation", "category": "participation",
        "percent": 88, "iep_goal_key": "", "iep_goal_id": "",
    })
    counter += 1
    gradebook["ART-101"].append({
        "row_id": f"GB-{counter:05d}", "date": assessment_days[2].isoformat(),
        "student_ref": "RIV-1007", "class_ref": "ART-101",
        "assignment": "Studio Effort", "category": "participation",
        "percent": 91, "iep_goal_key": "", "iep_goal_id": "",
    })

    # Malformed rows (wrong column count / non-numeric percent) for the quarantine demo.
    malformed = [
        ("BIO-101", "GB-90001,2026-09-30,RIV-1008,BIO-101,Biology Assessment 3,test"),  # too few cols
        ("MTH-101", "GB-90002,2026-10-14,RIV-1010,MTH-101,Math Assessment 4,test,not_a_number,,"),
    ]
    return gradebook, malformed


def _score_for(student_ref, class_ref, a_idx, goal_link) -> tuple[int, str, str, str]:
    """Deterministic percent + category + goal tag for one gradebook cell."""

    # Engineered finding (a): A. Sharma comprehension coursework averages ~40%.
    if student_ref == SHARMA and goal_link and goal_link[0] == SHARMA_GOAL2_KEY:
        idx = a_idx % len(SHARMA_GOAL2_PERCENTS)
        return (SHARMA_GOAL2_PERCENTS[idx], "assessment",
                SHARMA_GOAL2_KEY, _goal_id(SHARMA, SHARMA_GOAL2_KEY))

    baseline = _student_baseline(student_ref)
    rng = random.Random(f"{RANDOM_SEED}:{student_ref}:{class_ref}:{a_idx}")
    percent = max(35, min(100, baseline + rng.randint(-8, 8)))
    if goal_link:
        return percent, "assessment", goal_link[0], goal_link[1]
    return percent, "assessment", "", ""


# ── Service logs ─────────────────────────────────────────────────────────────
SERVICE_LOG_COLUMNS = [
    "row_id", "date", "student_ref", "service_key", "service_type",
    "provider_role", "minutes_delivered", "status",
]

# Per-student services that get delivery logs: (service_key, service_type, provider,
# mandate_min_per_session, sessions_per_week). Unstaffed services are logged as absent.
_SERVICE_PLAN = {
    "RIV-1001": [("sai-reading", "Specialized academic instruction (reading)",
                  "Special education teacher", 30, 5)],
    "RIV-1002": [(BELL_SERVICE_KEY, "Specialized academic instruction",
                  "Special education teacher", 30, 5),
                 ("counseling", "Individual counseling", "School counselor", 30, 1)],
    "RIV-1003": [("speech-therapy", "Speech and language therapy",
                  "Speech-language pathologist", 30, 2)],
    "RIV-1006": [("sai-math", "Specialized academic instruction (mathematics)",
                  "Special education teacher", 30, 5)],
}


def build_service_logs() -> dict[str, list[dict[str, Any]]]:
    weeks = _weeks()
    logs: dict[str, list[dict[str, Any]]] = {}
    counter = 0
    for student_ref, services in _SERVICE_PLAN.items():
        rows: list[dict[str, Any]] = []
        for service_key, service_type, provider, mandate, per_week in services:
            for week in weeks:
                session_days = week[:per_week]
                for day in session_days:
                    # Marcus's SAI is delivered 4 min short per session (20 min/wk under).
                    if student_ref == BELL and service_key == BELL_SERVICE_KEY:
                        minutes = BELL_DELIVERED_PER_SESSION
                    else:
                        minutes = mandate
                    counter += 1
                    rows.append({
                        "row_id": f"SL-{counter:05d}",
                        "date": day.isoformat(),
                        "student_ref": student_ref,
                        "service_key": service_key,
                        "service_type": service_type,
                        "provider_role": provider,
                        "minutes_delivered": minutes,
                        "status": "delivered",
                    })
        logs[student_ref] = rows
    return logs


# ── Teacher notes ────────────────────────────────────────────────────────────
def build_teacher_notes() -> list[dict[str, Any]]:
    """Structured teacher check-ins; one deliberately conflicts with the gradebook."""

    notes: list[dict[str, Any]] = []

    # Finding (a) conflict: positive narrative against ~40% comprehension data.
    notes.append(_note(
        "TN-0001", "2026-11-06", SHARMA, "ENG-101", "T-DELGADO",
        "Aanya is doing well with reading comprehension this quarter — she is engaged in "
        "discussion and I am pleased with her progress toward her main-idea goal.",
        goal_key="g2-comprehension"))

    # Normal, consistent notes for clean students.
    notes.append(_note(
        "TN-0002", "2026-11-06", "RIV-1007", "ENG-101", "T-DELGADO",
        "Grace is meeting expectations and using her coping strategy during transitions.",
        goal_key="g1-flexibility"))
    notes.append(_note(
        "TN-0003", "2026-11-06", "RIV-1010", "ENG-101", "T-DELGADO",
        "Jamal's reading fluency is improving steadily and matches his probe data.",
        goal_key="g1-fluency"))
    notes.append(_note(
        "TN-0004", "2026-11-06", BELL, "ENG-101", "T-LEE",
        "Marcus is starting tasks more independently; his SAI minutes have been light some "
        "weeks and I have flagged scheduling with the provider.",
        goal_key="g1-initiation"))

    # An unmappable check-in: references no measurable goal.
    notes.append(_note(
        "TN-0005", "2026-11-06", "RIV-1012", "ART-101", "T-FELDMAN",
        "Oscar brought in a sketchbook from home and was proud to show it to the class.",
        goal_key=None))
    return notes


def _note(note_id, day, student_ref, class_ref, teacher_ref, text, goal_key) -> dict[str, Any]:
    return {
        "note_id": note_id,
        "date": day,
        "student_ref": student_ref,
        "class_ref": class_ref,
        "teacher_ref": teacher_ref,
        "text": text,
        "iep_goal_key": goal_key,
        "iep_goal_id": _goal_id(student_ref, goal_key) if goal_key else None,
    }


# ── Accommodation confirmations (finding b) ──────────────────────────────────
CONFIRMATION_COLUMNS = [
    "row_id", "student_ref", "accommodation_key", "accommodation_id",
    "class_ref", "confirmed", "confirmed_by", "confirmed_at",
]


def build_confirmations() -> list[dict[str, Any]]:
    """Per-class confirmation state for accommodations that apply to all classes.

    Stands in for teacher brief-receipt audit events until the briefs pipeline exists.
    RIV-1001's extended-time is confirmed in 3 of 6 classes — the implementation gap.
    """

    rows: list[dict[str, Any]] = []
    counter = 0
    acc_id = stable_uuid("accommodation", SHARMA, SHARMA_EXTENDED_TIME_KEY)
    for class_ref in CORE_CLASS_REFS:
        confirmed = class_ref in SHARMA_CONFIRMED_CLASSES
        teacher = next(c["teachers_of_record"][0] for c in CLASSES if c["class_ref"] == class_ref)
        counter += 1
        rows.append({
            "row_id": f"CF-{counter:05d}",
            "student_ref": SHARMA,
            "accommodation_key": SHARMA_EXTENDED_TIME_KEY,
            "accommodation_id": acc_id,
            "class_ref": class_ref,
            "confirmed": "true" if confirmed else "false",
            "confirmed_by": teacher if confirmed else "",
            "confirmed_at": "2026-11-05T16:00:00Z" if confirmed else "",
        })

    # Clean control: another student's all-classes accommodation confirmed everywhere.
    control_id = stable_uuid("accommodation", "RIV-1008", "extended-time")
    for class_ref in CORE_CLASS_REFS:
        teacher = next(c["teachers_of_record"][0] for c in CLASSES if c["class_ref"] == class_ref)
        counter += 1
        rows.append({
            "row_id": f"CF-{counter:05d}",
            "student_ref": "RIV-1008",
            "accommodation_key": "extended-time",
            "accommodation_id": control_id,
            "class_ref": class_ref,
            "confirmed": "true",
            "confirmed_by": teacher,
            "confirmed_at": "2026-11-05T16:00:00Z",
        })
    return rows
