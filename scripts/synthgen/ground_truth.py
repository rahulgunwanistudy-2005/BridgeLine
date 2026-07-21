"""The 12 hand-authored canonical IEPRecords — the harness's ground truth.

These cap the credibility of every published metric, so the content (accommodations,
goals, services, disability language, date edge cases) is authored deliberately here.
The repetitive contract fields and stable IDs are filled by ``records.py`` so the output
is byte-stable. Each record is first-extraction: every reconciliation_status is null.

Edge cases (see also district.STUDENTS notes):
  - RIV-1001 A. Sharma  : extended-time applies across all classes (finding b); Goal 2 (finding a)
  - RIV-1002 M. Bell    : service whose delivery runs 20 min/wk short (finding c)
  - RIV-1003 S. Ramirez : one service with NO provider (Unassigned); triennial mid-semester
  - RIV-1004 E. Nakamura: already-overdue annual review (2026-10-30 < as_of 2026-11-13)
  - RIV-1005 L. Hassan  : annual review lands on a holiday (2026-11-11 Veterans Day)
  - RIV-1006 D. Torres  : mid-semester enrollment; member of the co-taught class
  - RIV-1007..1012      : clean records (no findings) so the dashboard is not all red
  - RIV-1012 O. (clean) : no progress report on file — last_progress_report is null with
                          field_confidences.last_progress_report = 0.0 (absent-field rule)

Each schema-v1.2 record embeds field_confidences: six 0.0–1.0 scores for the canonical
scalar/date fields. A null date scores 0.0.
"""

from __future__ import annotations

from typing import Any

from synthgen.constants import SCHOOL_YEAR
from synthgen.records import (
    UNASSIGNED_PROVIDER,
    AccommodationScopeReference,
    Scope,
    accommodation,
    field_confidences,
    goal,
    iep_record,
    scope_reference,
    service,
)


def _refs(*entries: tuple[Scope, str, float]) -> list[AccommodationScopeReference]:
    return [
        scope_reference(
            scope, ref, source_page=2, source_quote=ref, confidence=confidence
        )
        for scope, ref, confidence in entries
    ]


def _acc(
    sref: str,
    key: str,
    text: str,
    refs: list[AccommodationScopeReference],
    conf: float,
) -> dict[str, Any]:
    return accommodation(
        sref,
        key,
        text=text,
        applies_to_refs=refs,
        source_page=2,
        confidence=conf,
    )


def _svc(sref, key, type, mins, freq, provider, start, end, page, _quote, conf):
    return service(sref, key, type=type, minutes_per_week=mins, frequency=freq,
                   provider_role=provider, start=start, end=end, source_page=page,
                   confidence=conf)


def _goal(sref, key, text, baseline, target, measure, cadence, page, _quote, conf):
    return goal(sref, key, text=text, baseline=baseline, target=target, measure=measure,
                progress_cadence=cadence, source_page=page, confidence=conf)


# ── RIV-1001  Aanya Sharma — Specific learning disability (findings a + b) ────
def _riv_1001() -> dict[str, Any]:
    s = "RIV-1001"
    return iep_record(
        student_ref=s,
        disability_category="Specific learning disability",
        school_year=SCHOOL_YEAR,
        accommodations=[
            _acc(s, "extended-time", "Provide 50% extended time on all classroom tests and quizzes.",
                 _refs(("all", "across all classes", 0.94)), 0.95),
            _acc(s, "reduced-distraction", "Provide access to a reduced-distraction workspace.",
                 _refs(("all", "across all classes", 0.89)), 0.9),
            _acc(s, "text-to-speech", "Allow text-to-speech for instructional materials.",
                 _refs(("all", "across all classes", 0.87)), 0.88),
            _acc(s, "chunked-directions", "Break multi-step directions into chunked, numbered steps.",
                 _refs(("all", "across all classes", 0.84)), 0.86),
            _acc(s, "word-bank", "Provide a word bank for written-response items.",
                 _refs(("all", "across all classes", 0.82)), 0.83),
        ],
        services=[
            _svc(s, "sai-reading", "Specialized academic instruction (reading)", 150,
                 "30 minutes, 5 times weekly", "Special education teacher",
                 "2026-08-17", "2027-05-28", 3,
                 "Specialized academic instruction 30 minutes 5x weekly", 0.92),
        ],
        goals=[
            _goal(s, "g1-decoding",
                  "Given a grade-level passage, Aanya will decode multisyllabic words with 85% accuracy on 4 of 5 probes.",
                  "Decodes multisyllabic words with 55% accuracy.",
                  "85% accuracy on 4 of 5 consecutive probes.",
                  "Curriculum-based reading probe", "Every two weeks", 4,
                  "decode multisyllabic words with 85% accuracy", 0.9),
            _goal(s, "g2-comprehension",
                  "Given a grade-level text, Aanya will identify the main idea and two supporting details with 80% accuracy.",
                  "Identifies the main idea with 40% accuracy.",
                  "80% accuracy across three consecutive assessments.",
                  "Reading comprehension work sample", "Every two weeks", 4,
                  "identify the main idea and two supporting details with 80% accuracy", 0.87),
            _goal(s, "g3-writing",
                  "Aanya will write a five-sentence paragraph with a topic sentence and correct capitalization in 4 of 5 samples.",
                  "Writes two related sentences with inconsistent capitalization.",
                  "Five-sentence paragraph with topic sentence in 4 of 5 samples.",
                  "Writing work sample", "Monthly", 4,
                  "write a five-sentence paragraph with a topic sentence", 0.84),
        ],
        annual_review="2027-05-08", triennial_reeval="2028-09-15",
        last_progress_report="2026-10-30",
        field_confidences=field_confidences(student_ref=0.99, disability_category=0.97,
            school_year=0.99, annual_review=0.94, triennial_reeval=0.9, last_progress_report=0.93),
        page_count=4,
        legibility_scores=[1.0, 0.98, 0.97, 0.99],
    )


# ── RIV-1002  Marcus Bell — Autism (finding c: service runs 20 min/wk short) ──
def _riv_1002() -> dict[str, Any]:
    s = "RIV-1002"
    return iep_record(
        student_ref=s,
        disability_category="Autism",
        school_year=SCHOOL_YEAR,
        accommodations=[
            _acc(s, "visual-schedule", "Provide a written or visual schedule of activities for each period.",
                 _refs(("all", "in all settings", 0.92)), 0.93),
            _acc(s, "advance-warning", "Give advance warning before transitions and changes in routine.",
                 _refs(("all", "across all classes", 0.9)), 0.9),
            _acc(s, "sensory-breaks", "Allow scheduled sensory breaks of up to five minutes.",
                 _refs(("context", "during independent work", 0.86)), 0.88),
            _acc(s, "no-cold-call", "Do not require unplanned oral responses in front of the class.",
                 _refs(("context", "during whole-class discussion", 0.84)), 0.85),
        ],
        services=[
            # This mandate is 150 min/wk; the service log delivers ~130 → -20 min/wk variance.
            _svc(s, "sai-support", "Specialized academic instruction", 150,
                 "30 minutes, 5 times weekly", "Special education teacher",
                 "2026-08-17", "2027-05-28", 3,
                 "Specialized academic instruction 30 minutes 5 times weekly", 0.9),
            _svc(s, "counseling", "Individual counseling", 30,
                 "30 minutes, 1 time weekly", "School counselor",
                 "2026-08-17", "2027-05-28", 3,
                 "Individual counseling 30 minutes weekly", 0.87),
        ],
        goals=[
            _goal(s, "g1-initiation",
                  "Marcus will independently begin a classroom task within two minutes of the direction in 4 of 5 opportunities.",
                  "Begins a task within two minutes in 1 of 5 opportunities.",
                  "4 of 5 opportunities across two weeks.",
                  "Teacher observation checklist", "Weekly", 4,
                  "independently begin a classroom task within two minutes", 0.88),
            _goal(s, "g2-peer",
                  "Marcus will use a taught script to join a peer activity in 3 of 4 structured opportunities.",
                  "Joins a peer activity with adult prompting in 1 of 4 opportunities.",
                  "3 of 4 structured opportunities.",
                  "Structured social observation", "Weekly", 4,
                  "use a taught script to join a peer activity", 0.85),
        ],
        annual_review="2027-04-20", triennial_reeval="2029-01-12",
        last_progress_report="2026-10-16",
        field_confidences=field_confidences(student_ref=0.99, disability_category=0.96,
            school_year=0.99, annual_review=0.92, triennial_reeval=0.89, last_progress_report=0.9),
        page_count=4,
        legibility_scores=[1.0, 0.99, 0.98, 0.98],
    )


# ── RIV-1003  Sofia Ramirez — Speech/language (Unassigned provider; triennial mid-sem)
def _riv_1003() -> dict[str, Any]:
    s = "RIV-1003"
    return iep_record(
        student_ref=s,
        disability_category="Speech or language impairment",
        school_year=SCHOOL_YEAR,
        accommodations=[
            _acc(s, "extra-response-time", "Allow additional wait time for verbal responses.",
                 _refs(("all", "across all classes", 0.89)), 0.9),
            _acc(s, "sentence-starters", "Provide sentence starters for oral presentations.",
                 _refs(("subject", "English", 0.85)), 0.86),
            _acc(s, "no-penalize-articulation", "Do not penalize articulation errors in graded oral work.",
                 _refs(("subject", "English", 0.82),
                       ("context", "during oral presentations", 0.8)), 0.84),
        ],
        services=[
            _svc(s, "speech-therapy", "Speech and language therapy", 60,
                 "30 minutes, 2 times weekly", "Speech-language pathologist",
                 "2026-08-17", "2027-05-28", 3,
                 "Speech and language therapy 30 minutes twice weekly", 0.91),
            # Mandated but not yet staffed: provider is explicitly Unassigned.
            _svc(s, "language-support", "Language processing support (group)", 60,
                 "30 minutes, 2 times weekly", UNASSIGNED_PROVIDER,
                 "2026-08-17", "2027-05-28", 3,
                 "Language processing support group 30 minutes twice weekly; provider TBD", 0.72),
        ],
        goals=[
            _goal(s, "g1-articulation",
                  "Sofia will produce /r/ in the initial position of words with 80% accuracy in structured tasks.",
                  "Produces initial /r/ with 45% accuracy.",
                  "80% accuracy in structured tasks across three sessions.",
                  "Speech probe", "Weekly", 4,
                  "produce initial /r/ with 80% accuracy", 0.9),
            _goal(s, "g2-narrative",
                  "Sofia will retell a short narrative with a beginning, middle, and end in 4 of 5 opportunities.",
                  "Retells a narrative with only a beginning in 2 of 5 opportunities.",
                  "4 of 5 opportunities.",
                  "Language sample", "Every two weeks", 4,
                  "retell a short narrative with a beginning, middle, and end", 0.86),
        ],
        annual_review="2027-03-03",
        triennial_reeval="2026-11-20",  # triennial due mid-semester
        last_progress_report="2026-10-09",
        field_confidences=field_confidences(student_ref=0.99, disability_category=0.95,
            school_year=0.99, annual_review=0.9, triennial_reeval=0.93, last_progress_report=0.88),
        page_count=4,
        legibility_scores=[1.0, 0.98, 0.99, 0.97],
    )


# ── RIV-1004  Ethan Nakamura — OHI/ADHD (overdue annual review) ───────────────
def _riv_1004() -> dict[str, Any]:
    s = "RIV-1004"
    return iep_record(
        student_ref=s,
        disability_category="Other health impairment (ADHD)",
        school_year=SCHOOL_YEAR,
        accommodations=[
            _acc(s, "extended-time", "Provide 50% extended time on tests and long assignments.",
                 _refs(("subject", "all academic subjects", 0.51)), 0.93),
            _acc(s, "preferential-seating", "Seat near the point of instruction and away from high-traffic areas.",
                 _refs(("all", "in all settings", 0.9)), 0.91),
            _acc(s, "movement-breaks", "Permit brief movement breaks between tasks.",
                 _refs(("context", "between classroom tasks", 0.86)), 0.87),
            _acc(s, "assignment-checklist", "Provide a checklist to break long assignments into steps.",
                 _refs(("context", "during long assignments", 0.84)), 0.85),
            _acc(s, "planner-check", "Check the daily planner for recorded homework before dismissal.",
                 _refs(("context", "before dismissal", 0.8)), 0.82),
        ],
        services=[
            _svc(s, "sai-organization", "Specialized academic instruction (executive functioning)", 100,
                 "50 minutes, 2 times weekly", "Special education teacher",
                 "2026-08-17", "2027-05-28", 3,
                 "Specialized academic instruction executive functioning 50 minutes twice weekly", 0.89),
        ],
        goals=[
            _goal(s, "g1-task-completion",
                  "Ethan will complete and submit in-class assignments in 4 of 5 opportunities without redirection.",
                  "Completes in-class assignments in 2 of 5 opportunities.",
                  "4 of 5 opportunities.",
                  "Work-completion log", "Weekly", 4,
                  "complete and submit in-class assignments in 4 of 5 opportunities", 0.88),
            _goal(s, "g2-materials",
                  "Ethan will arrive to class with required materials in 8 of 10 class days.",
                  "Arrives with required materials in 3 of 10 class days.",
                  "8 of 10 class days.",
                  "Teacher checklist", "Weekly", 4,
                  "arrive to class with required materials in 8 of 10 class days", 0.85),
        ],
        annual_review="2026-10-30",  # OVERDUE relative to as_of 2026-11-13
        triennial_reeval="2028-05-30",
        last_progress_report="2026-09-25",
        field_confidences=field_confidences(student_ref=0.99, disability_category=0.94,
            school_year=0.99, annual_review=0.95, triennial_reeval=0.88, last_progress_report=0.91),
        page_count=4,
        legibility_scores=[1.0, 0.97, 0.98, 0.99],
    )


# ── RIV-1005  Layla Hassan — Hearing impairment (review lands on a holiday) ───
def _riv_1005() -> dict[str, Any]:
    s = "RIV-1005"
    return iep_record(
        student_ref=s,
        disability_category="Hearing impairment",
        school_year=SCHOOL_YEAR,
        accommodations=[
            _acc(s, "fm-system", "Use the personal FM/DM listening system in every class.",
                 _refs(("all", "across all classes", 0.93)), 0.94),
            _acc(s, "preferential-seating", "Seat with a clear line of sight to the face of the speaker.",
                 _refs(("all", "in all settings", 0.91)), 0.92),
            _acc(s, "captioned-media", "Provide captions or a transcript for all audio and video media.",
                 _refs(("all", "across all classes", 0.9)), 0.9),
            _acc(s, "visual-alerts", "Pair auditory alerts and directions with a visual cue.",
                 _refs(("context", "during verbal instruction", 0.86)), 0.87),
            _acc(s, "notetaker", "Provide a peer notetaker or copy of lecture notes.",
                 _refs(("subject", "English", 0.83),
                       ("subject", "World History", 0.82)), 0.84),
        ],
        services=[
            _svc(s, "dhh-itinerant", "Deaf/hard-of-hearing itinerant support", 60,
                 "30 minutes, 2 times weekly", "Teacher of the deaf and hard of hearing",
                 "2026-08-17", "2027-05-28", 3,
                 "Deaf/hard-of-hearing itinerant support 30 minutes twice weekly", 0.9),
            _svc(s, "audiology", "Educational audiology consultation", 30,
                 "30 minutes, 1 time monthly", "Educational audiologist",
                 "2026-08-17", "2027-05-28", 3,
                 "Educational audiology consultation 30 minutes monthly", 0.83),
        ],
        goals=[
            _goal(s, "g1-selfadvocacy",
                  "Layla will independently report FM system problems to the teacher in 4 of 5 opportunities.",
                  "Reports FM system problems with prompting in 1 of 5 opportunities.",
                  "4 of 5 opportunities.",
                  "Teacher observation", "Every two weeks", 4,
                  "independently report FM system problems in 4 of 5 opportunities", 0.88),
            _goal(s, "g2-vocabulary",
                  "Layla will define grade-level academic vocabulary with 80% accuracy.",
                  "Defines grade-level vocabulary with 50% accuracy.",
                  "80% accuracy across three assessments.",
                  "Vocabulary probe", "Monthly", 4,
                  "define grade-level academic vocabulary with 80% accuracy", 0.85),
        ],
        annual_review="2026-11-11",  # lands on Veterans Day (a holiday)
        triennial_reeval="2028-11-09",
        last_progress_report="2026-10-16",
        field_confidences=field_confidences(student_ref=0.99, disability_category=0.96,
            school_year=0.99, annual_review=0.93, triennial_reeval=0.89, last_progress_report=0.9),
        page_count=4,
        legibility_scores=[1.0, 0.99, 0.98, 0.99],
    )


# ── RIV-1006  Diego Torres — SLD (mid-semester enrollment; co-taught class) ───
def _riv_1006() -> dict[str, Any]:
    s = "RIV-1006"
    return iep_record(
        student_ref=s,
        disability_category="Specific learning disability",
        school_year=SCHOOL_YEAR,
        accommodations=[
            _acc(s, "extended-time", "Provide 50% extended time on classroom assessments.",
                 _refs(("subject", "Mathematics", 0.91),
                       ("subject", "Biology", 0.89)), 0.93),
            _acc(s, "calculator", "Allow a four-function calculator on non-calculation-skill tasks.",
                 _refs(("subject", "Mathematics", 0.86)), 0.87),
            _acc(s, "graphic-organizer", "Provide graphic organizers for writing and note-taking.",
                 _refs(("subject", "English", 0.84),
                       ("context", "during written assignments", 0.82)), 0.85),
            _acc(s, "read-aloud", "Read test directions and math word problems aloud on request.",
                 _refs(("context", "during testing", 0.81)), 0.83),
        ],
        services=[
            _svc(s, "sai-math", "Specialized academic instruction (mathematics)", 150,
                 "30 minutes, 5 times weekly", "Special education teacher",
                 "2026-10-05", "2027-05-28", 3,  # begins at his mid-semester enrollment
                 "Specialized academic instruction mathematics 30 minutes 5 times weekly", 0.9),
        ],
        goals=[
            _goal(s, "g1-computation",
                  "Diego will solve two-step equations with 80% accuracy on 4 of 5 probes.",
                  "Solves two-step equations with 40% accuracy.",
                  "80% accuracy on 4 of 5 probes.",
                  "Math curriculum-based probe", "Every two weeks", 4,
                  "solve two-step equations with 80% accuracy", 0.88),
            _goal(s, "g2-writtenexpression",
                  "Diego will write a paragraph with a clear topic sentence and three details in 4 of 5 samples.",
                  "Writes a paragraph with a topic sentence in 1 of 5 samples.",
                  "4 of 5 samples.",
                  "Writing work sample", "Monthly", 4,
                  "write a paragraph with a clear topic sentence and three details", 0.84),
        ],
        annual_review="2027-05-15", triennial_reeval="2029-02-27",
        last_progress_report="2026-10-30",
        field_confidences=field_confidences(student_ref=0.99, disability_category=0.95,
            school_year=0.99, annual_review=0.92, triennial_reeval=0.88, last_progress_report=0.9),
        page_count=4,
        legibility_scores=[1.0, 0.98, 0.98, 0.97],
    )


# ── RIV-1007..1012 : clean records, no findings ──────────────────────────────
def _riv_1007() -> dict[str, Any]:
    s = "RIV-1007"
    return iep_record(
        student_ref=s, disability_category="Autism", school_year=SCHOOL_YEAR,
        accommodations=[
            _acc(s, "visual-supports", "Provide visual supports and models for new tasks.",
                 _refs(("all", "across all classes", 0.91)), 0.92),
            _acc(s, "transition-warning", "Give a two-minute warning before transitions.",
                 _refs(("all", "in all settings", 0.89)), 0.9),
            _acc(s, "quiet-space", "Allow access to a designated quiet space when overwhelmed.",
                 _refs(("context", "when overwhelmed", 0.86)), 0.87),
        ],
        services=[
            _svc(s, "sai", "Specialized academic instruction", 100,
                 "50 minutes, 2 times weekly", "Special education teacher",
                 "2026-08-17", "2027-05-28", 3,
                 "Specialized academic instruction 50 minutes twice weekly", 0.9),
            _svc(s, "ot", "Occupational therapy", 30,
                 "30 minutes, 1 time weekly", "Occupational therapist",
                 "2026-08-17", "2027-05-28", 3,
                 "Occupational therapy 30 minutes weekly", 0.86),
        ],
        goals=[
            _goal(s, "g1-flexibility",
                  "Grace will accept a change in routine using a coping strategy in 4 of 5 opportunities.",
                  "Accepts a change in routine in 2 of 5 opportunities.",
                  "4 of 5 opportunities.", "Teacher observation", "Weekly", 4,
                  "accept a change in routine using a coping strategy", 0.88),
            _goal(s, "g2-writing",
                  "Grace will produce three organized sentences on a topic in 4 of 5 samples.",
                  "Produces one sentence on a topic in 2 of 5 samples.",
                  "4 of 5 samples.", "Writing work sample", "Monthly", 4,
                  "produce three organized sentences on a topic", 0.85),
        ],
        annual_review="2027-02-18", triennial_reeval="2028-10-05",
        last_progress_report="2026-10-16",
        field_confidences=field_confidences(student_ref=0.99, disability_category=0.96,
            school_year=0.99, annual_review=0.93, triennial_reeval=0.9, last_progress_report=0.92),
        page_count=4,
        legibility_scores=[1.0, 0.99, 0.99, 0.98],
    )


def _riv_1008() -> dict[str, Any]:
    s = "RIV-1008"
    return iep_record(
        student_ref=s, disability_category="Other health impairment (ADHD)", school_year=SCHOOL_YEAR,
        accommodations=[
            _acc(s, "extended-time", "Provide 25% extended time on timed assessments.",
                 _refs(("context", "during timed assessments", 0.89)), 0.9),
            _acc(s, "chunked-work", "Break long assignments into smaller submitted parts.",
                 _refs(("context", "during long assignments", 0.84)), 0.86),
            _acc(s, "frequent-checkins", "Provide frequent check-ins for understanding.",
                 _refs(("all", "across all classes", 0.83)), 0.84),
        ],
        services=[
            _svc(s, "sai", "Specialized academic instruction", 100,
                 "50 minutes, 2 times weekly", "Special education teacher",
                 "2026-08-17", "2027-05-28", 3,
                 "Specialized academic instruction 50 minutes twice weekly", 0.89),
        ],
        goals=[
            _goal(s, "g1-focus",
                  "Noah will sustain attention to an independent task for 10 minutes in 4 of 5 opportunities.",
                  "Sustains attention for 3 minutes in 2 of 5 opportunities.",
                  "4 of 5 opportunities.", "Teacher observation", "Weekly", 4,
                  "sustain attention to an independent task for 10 minutes", 0.87),
            _goal(s, "g2-selfmonitor",
                  "Noah will use a self-monitoring checklist to review work before submitting in 4 of 5 samples.",
                  "Reviews work before submitting in 1 of 5 samples.",
                  "4 of 5 samples.", "Work sample", "Every two weeks", 4,
                  "use a self-monitoring checklist to review work before submitting", 0.85),
        ],
        annual_review="2027-01-27", triennial_reeval="2029-03-14",
        last_progress_report="2026-10-16",
        field_confidences=field_confidences(student_ref=0.99, disability_category=0.96,
            school_year=0.99, annual_review=0.93, triennial_reeval=0.9, last_progress_report=0.92),
        page_count=4,
        legibility_scores=[1.0, 0.98, 0.99, 0.99],
    )


def _riv_1009() -> dict[str, Any]:
    s = "RIV-1009"
    return iep_record(
        student_ref=s, disability_category="Speech or language impairment", school_year=SCHOOL_YEAR,
        accommodations=[
            _acc(s, "wait-time", "Allow additional wait time for verbal responses.",
                 _refs(("all", "across all classes", 0.89)), 0.9),
            _acc(s, "visual-vocab", "Pair new vocabulary with visuals and definitions.",
                 _refs(("subject", "English", 0.85),
                       ("subject", "Biology", 0.83)), 0.86),
            _acc(s, "repeat-directions", "Repeat and rephrase spoken directions on request.",
                 _refs(("context", "during verbal instruction", 0.82)), 0.84),
        ],
        services=[
            _svc(s, "speech", "Speech and language therapy", 60,
                 "30 minutes, 2 times weekly", "Speech-language pathologist",
                 "2026-08-17", "2027-05-28", 3,
                 "Speech and language therapy 30 minutes twice weekly", 0.91),
        ],
        goals=[
            _goal(s, "g1-grammar",
                  "Priya will use correct past-tense verbs in structured sentences with 80% accuracy.",
                  "Uses correct past-tense verbs with 50% accuracy.",
                  "80% accuracy across three sessions.", "Language sample", "Weekly", 4,
                  "use correct past-tense verbs with 80% accuracy", 0.89),
            _goal(s, "g2-following-directions",
                  "Priya will follow two-step spoken directions in 4 of 5 opportunities.",
                  "Follows two-step directions in 2 of 5 opportunities.",
                  "4 of 5 opportunities.", "Teacher observation", "Every two weeks", 4,
                  "follow two-step spoken directions in 4 of 5 opportunities", 0.86),
        ],
        annual_review="2027-04-06", triennial_reeval="2028-12-01",
        last_progress_report="2026-10-30",
        field_confidences=field_confidences(student_ref=0.99, disability_category=0.96,
            school_year=0.99, annual_review=0.93, triennial_reeval=0.9, last_progress_report=0.92),
        page_count=4,
        legibility_scores=[1.0, 0.99, 0.98, 0.99],
    )


def _riv_1010() -> dict[str, Any]:
    s = "RIV-1010"
    return iep_record(
        student_ref=s, disability_category="Specific learning disability", school_year=SCHOOL_YEAR,
        accommodations=[
            _acc(s, "audiobooks", "Provide audio versions of grade-level texts.",
                 _refs(("subject", "English", 0.89)), 0.9),
            _acc(s, "spelling-not-graded", "Do not grade spelling on first-draft written work.",
                 _refs(("subject", "English", 0.84),
                       ("context", "during written assignments", 0.82)), 0.86),
            _acc(s, "extended-time", "Provide 50% extended time on reading-heavy assessments.",
                 _refs(("subject", "English", 0.9),
                       ("context", "during testing", 0.88)), 0.92),
            _acc(s, "copy-of-notes", "Provide a copy of teacher notes.",
                 _refs(("subject", "World History", 0.81),
                       ("subject", "Biology", 0.8)), 0.83),
        ],
        services=[
            _svc(s, "sai-reading", "Specialized academic instruction (reading)", 150,
                 "30 minutes, 5 times weekly", "Special education teacher",
                 "2026-08-17", "2027-05-28", 3,
                 "Specialized academic instruction reading 30 minutes 5 times weekly", 0.9),
        ],
        goals=[
            _goal(s, "g1-fluency",
                  "Jamal will read grade-level text at 120 words per minute with 95% accuracy.",
                  "Reads grade-level text at 80 words per minute.",
                  "120 words per minute with 95% accuracy.", "Oral reading fluency probe", "Every two weeks", 4,
                  "read grade-level text at 120 words per minute with 95% accuracy", 0.88),
            _goal(s, "g2-comprehension",
                  "Jamal will answer inferential questions about a text with 80% accuracy.",
                  "Answers inferential questions with 50% accuracy.",
                  "80% accuracy across three assessments.", "Comprehension work sample", "Every two weeks", 4,
                  "answer inferential questions about a text with 80% accuracy", 0.85),
            _goal(s, "g3-writing",
                  "Jamal will organize a multi-paragraph response using an outline in 4 of 5 samples.",
                  "Organizes a response without an outline in 2 of 5 samples.",
                  "4 of 5 samples.", "Writing work sample", "Monthly", 4,
                  "organize a multi-paragraph response using an outline", 0.83),
        ],
        annual_review="2027-03-24", triennial_reeval="2029-04-18",
        last_progress_report="2026-10-30",
        field_confidences=field_confidences(student_ref=0.99, disability_category=0.96,
            school_year=0.99, annual_review=0.93, triennial_reeval=0.9, last_progress_report=0.92),
        page_count=4,
        legibility_scores=[1.0, 0.98, 0.98, 0.98],
    )


def _riv_1011() -> dict[str, Any]:
    s = "RIV-1011"
    return iep_record(
        student_ref=s, disability_category="Hearing impairment", school_year=SCHOOL_YEAR,
        accommodations=[
            _acc(s, "fm-system", "Use the personal FM/DM listening system in every class.",
                 _refs(("all", "across all classes", 0.92)), 0.93),
            _acc(s, "captioned-media", "Provide captions or a transcript for audio and video media.",
                 _refs(("all", "in all settings", 0.89)), 0.9),
            _acc(s, "face-speaker", "Face the student when speaking and avoid covering the mouth.",
                 _refs(("context", "during verbal instruction", 0.84)), 0.86),
        ],
        services=[
            _svc(s, "dhh-itinerant", "Deaf/hard-of-hearing itinerant support", 60,
                 "30 minutes, 2 times weekly", "Teacher of the deaf and hard of hearing",
                 "2026-08-17", "2027-05-28", 3,
                 "Deaf/hard-of-hearing itinerant support 30 minutes twice weekly", 0.9),
        ],
        goals=[
            _goal(s, "g1-vocabulary",
                  "Emma will define grade-level academic vocabulary with 80% accuracy.",
                  "Defines grade-level vocabulary with 55% accuracy.",
                  "80% accuracy across three assessments.", "Vocabulary probe", "Monthly", 4,
                  "define grade-level academic vocabulary with 80% accuracy", 0.88),
            _goal(s, "g2-selfadvocacy",
                  "Emma will request clarification when she misses information in 4 of 5 opportunities.",
                  "Requests clarification in 1 of 5 opportunities.",
                  "4 of 5 opportunities.", "Teacher observation", "Every two weeks", 4,
                  "request clarification when she misses information", 0.85),
        ],
        annual_review="2027-02-02", triennial_reeval="2028-09-28",
        last_progress_report="2026-10-16",
        field_confidences=field_confidences(student_ref=0.99, disability_category=0.96,
            school_year=0.99, annual_review=0.93, triennial_reeval=0.9, last_progress_report=0.92),
        page_count=4,
        legibility_scores=[1.0, 0.99, 0.99, 0.98],
    )


def _riv_1012() -> dict[str, Any]:
    s = "RIV-1012"
    return iep_record(
        student_ref=s, disability_category="Autism", school_year=SCHOOL_YEAR,
        accommodations=[
            _acc(s, "visual-schedule", "Provide a visual schedule for each class period.",
                 _refs(("all", "across all classes", 0.91)), 0.92),
            _acc(s, "clear-expectations", "State task expectations explicitly and in writing.",
                 _refs(("all", "in all settings", 0.88)), 0.89),
            _acc(s, "reduced-writing", "Accept typed responses in place of extended handwriting.",
                 _refs(("subject", "English", 0.83),
                       ("context", "during written assignments", 0.81)), 0.85),
            _acc(s, "sensory-breaks", "Allow brief scheduled sensory breaks.",
                 _refs(("context", "during independent work", 0.81)), 0.83),
        ],
        services=[
            _svc(s, "sai", "Specialized academic instruction", 100,
                 "50 minutes, 2 times weekly", "Special education teacher",
                 "2026-08-17", "2027-05-28", 3,
                 "Specialized academic instruction 50 minutes twice weekly", 0.9),
            _svc(s, "speech-social", "Speech and language therapy (social communication)", 30,
                 "30 minutes, 1 time weekly", "Speech-language pathologist",
                 "2026-08-17", "2027-05-28", 3,
                 "Speech and language therapy social communication 30 minutes weekly", 0.86),
        ],
        goals=[
            _goal(s, "g1-conversation",
                  "Oscar will maintain a topic across three conversational turns in 4 of 5 opportunities.",
                  "Maintains a topic for one turn in 2 of 5 opportunities.",
                  "4 of 5 opportunities.", "Structured social observation", "Weekly", 4,
                  "maintain a topic across three conversational turns", 0.87),
            _goal(s, "g2-organization",
                  "Oscar will use a checklist to organize materials for each class in 8 of 10 days.",
                  "Organizes materials in 3 of 10 days.",
                  "8 of 10 days.", "Teacher checklist", "Weekly", 4,
                  "use a checklist to organize materials for each class", 0.84),
        ],
        annual_review="2027-05-19", triennial_reeval="2029-01-30",
        # No progress report on file yet: absent date scores 0.0 confidence (schema rule).
        last_progress_report=None,
        field_confidences=field_confidences(student_ref=0.99, disability_category=0.96,
            school_year=0.99, annual_review=0.93, triennial_reeval=0.9, last_progress_report=0.0),
        page_count=4,
        legibility_scores=[1.0, 0.98, 0.99, 0.97],
    )


# Ordered registry of the 12 record builders (confidences are embedded in each record).
_BUILDERS: list[Any] = [
    _riv_1001, _riv_1002, _riv_1003, _riv_1004, _riv_1005, _riv_1006,
    _riv_1007, _riv_1008, _riv_1009, _riv_1010, _riv_1011, _riv_1012,
]


def build_records() -> list[dict[str, Any]]:
    """Return the 12 canonical IEPRecords (field_confidences embedded), in order."""

    return [build() for build in _BUILDERS]
