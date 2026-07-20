"""The single source of truth for Riverside Demo School District structure.

Everything downstream — ground-truth IEPs, gradebooks, service logs, rosters, rendered
documents, and the seed loader — derives from the values here, so the roster, gradebook,
service log, and IEP records cannot disagree. All data is obviously fictional.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from synthgen.constants import (
    AS_OF,
    DISTRICT_NAME,
    SCHOOL_NAME,
    SCHOOL_YEAR,
    SEMESTER_FIRST_DAY,
    SEMESTER_LAST_DAY,
    stable_uuid,
)

SCHOOL_REF = "RIV-HS"

# ── Subjects (6) ─────────────────────────────────────────────────────────────
SUBJECTS: list[dict[str, str]] = [
    {"subject_ref": "ENG", "name": "English"},
    {"subject_ref": "MTH", "name": "Mathematics"},
    {"subject_ref": "BIO", "name": "Biology"},
    {"subject_ref": "HIS", "name": "World History"},
    {"subject_ref": "PE", "name": "Physical Education"},
    {"subject_ref": "ART", "name": "Art"},
]

# ── Teachers (8) ─────────────────────────────────────────────────────────────
# Six subject teachers + one special educator (co-teacher / case manager) + one SLP.
TEACHERS: list[dict[str, str]] = [
    {"teacher_ref": "T-DELGADO", "display_name": "Ms. Renata Delgado", "role": "English teacher"},
    {"teacher_ref": "T-OKAFOR", "display_name": "Mr. Samuel Okafor", "role": "Mathematics teacher"},
    {"teacher_ref": "T-CHEN", "display_name": "Dr. Mia Chen", "role": "Biology teacher"},
    {"teacher_ref": "T-PORTER", "display_name": "Ms. Ana Porter", "role": "World History teacher"},
    {"teacher_ref": "T-RIVERA", "display_name": "Coach Luis Rivera", "role": "Physical Education teacher"},
    {"teacher_ref": "T-FELDMAN", "display_name": "Mr. David Feldman", "role": "Art teacher"},
    {"teacher_ref": "T-LEE", "display_name": "Ms. Jordan Lee", "role": "Special education teacher"},
    {"teacher_ref": "T-ALVAREZ", "display_name": "Ms. Carmen Alvarez", "role": "Speech-language pathologist"},
]

# ── Classes (6, one section per subject) ─────────────────────────────────────
# ENG-101 is CO-TAUGHT: two teachers of record (general educator + special educator).
CLASSES: list[dict[str, Any]] = [
    {"class_ref": "ENG-101", "name": "English 9 (Co-taught)", "subject_ref": "ENG",
     "period": 1, "teachers_of_record": ["T-DELGADO", "T-LEE"]},
    {"class_ref": "MTH-101", "name": "Algebra I", "subject_ref": "MTH",
     "period": 2, "teachers_of_record": ["T-OKAFOR"]},
    {"class_ref": "BIO-101", "name": "Biology", "subject_ref": "BIO",
     "period": 3, "teachers_of_record": ["T-CHEN"]},
    {"class_ref": "HIS-101", "name": "World History", "subject_ref": "HIS",
     "period": 4, "teachers_of_record": ["T-PORTER"]},
    {"class_ref": "PE-101", "name": "Physical Education", "subject_ref": "PE",
     "period": 5, "teachers_of_record": ["T-RIVERA"]},
    {"class_ref": "ART-101", "name": "Art Foundations", "subject_ref": "ART",
     "period": 6, "teachers_of_record": ["T-FELDMAN"]},
]

CORE_CLASS_REFS: list[str] = [c["class_ref"] for c in CLASSES]

# ── Students (12) ────────────────────────────────────────────────────────────
# finding/edge-case tags are documentation only; the actual data lives in ground_truth.py
STUDENTS: list[dict[str, str]] = [
    {"student_ref": "RIV-1001", "display_name": "Aanya Sharma", "short_name": "A. Sharma",
     "category": "Specific learning disability", "note": "findings a+b"},
    {"student_ref": "RIV-1002", "display_name": "Marcus Bell", "short_name": "M. Bell",
     "category": "Autism", "note": "finding c: service -20 min/wk"},
    {"student_ref": "RIV-1003", "display_name": "Sofia Ramirez", "short_name": "S. Ramirez",
     "category": "Speech or language impairment", "note": "unassigned provider; triennial mid-semester"},
    {"student_ref": "RIV-1004", "display_name": "Ethan Nakamura", "short_name": "E. Nakamura",
     "category": "Other health impairment (ADHD)", "note": "overdue annual review"},
    {"student_ref": "RIV-1005", "display_name": "Layla Hassan", "short_name": "L. Hassan",
     "category": "Hearing impairment", "note": "annual review lands on a holiday"},
    {"student_ref": "RIV-1006", "display_name": "Diego Torres", "short_name": "D. Torres",
     "category": "Specific learning disability", "note": "mid-semester enrollment; co-taught class"},
    {"student_ref": "RIV-1007", "display_name": "Grace Kim", "short_name": "G. Kim",
     "category": "Autism", "note": "clean, no findings"},
    {"student_ref": "RIV-1008", "display_name": "Noah Williams", "short_name": "N. Williams",
     "category": "Other health impairment (ADHD)", "note": "clean, no findings"},
    {"student_ref": "RIV-1009", "display_name": "Priya Patel", "short_name": "P. Patel",
     "category": "Speech or language impairment", "note": "clean, no findings"},
    {"student_ref": "RIV-1010", "display_name": "Jamal Carter", "short_name": "J. Carter",
     "category": "Specific learning disability", "note": "clean, no findings"},
    {"student_ref": "RIV-1011", "display_name": "Emma Johansson", "short_name": "E. Johansson",
     "category": "Hearing impairment", "note": "clean, no findings"},
    {"student_ref": "RIV-1012", "display_name": "Oscar Nguyen", "short_name": "O. Nguyen",
     "category": "Autism", "note": "clean; one unmapped progress signal"},
]

# Diego Torres enrolls mid-semester; everyone else on the first instructional day.
MID_SEMESTER_ENROLLMENT = {"student_ref": "RIV-1006", "start": date(2026, 10, 5)}

# ── Calendar (Fall 2026) ─────────────────────────────────────────────────────
INSTRUCTIONAL_WEEKDAYS = [0, 1, 2, 3, 4]  # Monday–Friday
HOLIDAYS: list[dict[str, str]] = [
    {"date": "2026-09-07", "name": "Labor Day"},
    {"date": "2026-10-09", "name": "Staff Development Day (no school)"},
    {"date": "2026-10-12", "name": "Indigenous Peoples' Day"},
    {"date": "2026-11-11", "name": "Veterans Day"},
    {"date": "2026-11-25", "name": "Thanksgiving Break"},
    {"date": "2026-11-26", "name": "Thanksgiving Break"},
    {"date": "2026-11-27", "name": "Thanksgiving Break"},
]


def _instructional_days() -> list[str]:
    """Materialize every instructional day: weekdays in-bounds minus holidays."""

    holiday_dates = {h["date"] for h in HOLIDAYS}
    days: list[str] = []
    cursor = SEMESTER_FIRST_DAY
    while cursor <= SEMESTER_LAST_DAY:
        iso = cursor.isoformat()
        if cursor.weekday() in INSTRUCTIONAL_WEEKDAYS and iso not in holiday_dates:
            days.append(iso)
        cursor += timedelta(days=1)
    return days


def build_district() -> dict[str, Any]:
    """Assemble the full district document with stable UUIDs for every entity."""

    instructional_days = _instructional_days()
    return {
        "district": {"name": DISTRICT_NAME, "synthetic": True},
        "school": {
            "id": stable_uuid("school", SCHOOL_REF),
            "school_ref": SCHOOL_REF,
            "name": SCHOOL_NAME,
            "school_year": SCHOOL_YEAR,
        },
        "subjects": [{"id": stable_uuid("subject", s["subject_ref"]), **s} for s in SUBJECTS],
        "teachers": [
            {"id": stable_uuid("teacher", t["teacher_ref"]),
             "email": f"{t['teacher_ref'].removeprefix('T-').lower()}@riverside-demo.example",
             **t}
            for t in TEACHERS
        ],
        "classes": [
            {"id": stable_uuid("class", c["class_ref"]), "school_year": SCHOOL_YEAR,
             "teacher_ids": [stable_uuid("teacher", t) for t in c["teachers_of_record"]], **c}
            for c in CLASSES
        ],
        "students": [{"id": stable_uuid("student", s["student_ref"]), **s} for s in STUDENTS],
        "enrollments": _build_enrollments(),
        "calendar": {
            "school_year": SCHOOL_YEAR,
            "semester": "Fall 2026",
            "first_instructional_day": SEMESTER_FIRST_DAY.isoformat(),
            "last_instructional_day": SEMESTER_LAST_DAY.isoformat(),
            "instructional_weekdays": INSTRUCTIONAL_WEEKDAYS,
            "as_of": AS_OF.isoformat(),
            "holidays": HOLIDAYS,
            "instructional_day_count": len(instructional_days),
            "instructional_days": instructional_days,
        },
    }


def _build_enrollments() -> list[dict[str, Any]]:
    """Every student is enrolled in all six core classes; Diego enrolls mid-semester."""

    enrollments: list[dict[str, Any]] = []
    for student in STUDENTS:
        sref = student["student_ref"]
        start = (
            MID_SEMESTER_ENROLLMENT["start"].isoformat()
            if sref == MID_SEMESTER_ENROLLMENT["student_ref"]
            else SEMESTER_FIRST_DAY.isoformat()
        )
        for class_ref in CORE_CLASS_REFS:
            enrollments.append({
                "id": stable_uuid("enrollment", sref, class_ref),
                "student_ref": sref,
                "class_ref": class_ref,
                "start": start,
                "end": None,
            })
    return enrollments
