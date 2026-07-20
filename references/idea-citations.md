# IDEA Part B Citation Spec — Bridgeline Compliance Rules

Source of truth for cx/02's rules engine. Every rule below traces to 34 CFR Part 300, Subpart D.

---

RULE: teacher-access
CITE: 34 CFR §300.323(d)(1)
PLAIN: The public agency must ensure the child's IEP is accessible to each regular education
       teacher, special education teacher, related services provider, and any other service
       provider responsible for its implementation.
DERIVES: For each student, an Obligation granting IEP-read-access to every teacher/provider
         who is a teacher-of-record or service-provider-of-record for that student in the
         current school year.

---

RULE: teacher-informed-responsibilities
CITE: 34 CFR §300.323(d)(2)(i)
PLAIN: Each teacher and provider described in (d)(1) must be informed of his or her specific
       responsibilities related to implementing the child's IEP.
DERIVES: For each student × each teacher/provider-of-record, an Obligation stating that
         teacher's specific implementation responsibility for that student (the spine of the
         per-teacher brief).

---

RULE: teacher-informed-accommodations
CITE: 34 CFR §300.323(d)(2)(ii)
PLAIN: Each teacher and provider described in (d)(1) must be informed of the specific
       accommodations, modifications, and supports that must be provided for the child in
       accordance with the IEP.
DERIVES: For each accommodation × each teacher-of-record for a context (subject/class) the
         accommodation applies to, an Obligation naming that exact accommodation. This is
         the core Family-1 fan-out rule — the one that turns "the IEP exists" into
         "eleven specific people have eleven specific duties."

---

RULE: services-without-delay
CITE: 34 CFR §300.323(c)(2)
PLAIN: As soon as possible following development of the IEP, special education and related
       services must be made available to the child in accordance with the child's IEP.
DERIVES: A Finding if a service's start date lags materially behind IEP approval with no
         documented reason — feeds Family 4 (implementation-gap detection).

---

RULE: initial-iep-meeting-30-days
CITE: 34 CFR §300.323(c)(1)
PLAIN: A meeting to develop an IEP for a child must be conducted within 30 days of a
       determination that the child needs special education and related services.
DERIVES: A deadline/calendar entry for students in initial-eligibility status (not the
         annual-review cadence — this is the one-time initial-development clock). Scope
         note: Bridgeline's MVP dataset is all students with existing approved IEPs, so this
         rule may not fire in the demo dataset — implement it, but don't force a demo beat
         around it.

---

RULE: annual-review
CITE: 34 CFR §300.324(b)(1)(i)
PLAIN: The public agency must ensure the IEP Team reviews the child's IEP periodically, but
       not less than annually, to determine whether the annual goals are being achieved.
DERIVES: A calendar entry per student: annual_review deadline = last review date + 1 year.
         30/14/3-day lead-time warnings per the branch file. This is the deadline the demo's
         "one overdue annual review" scenario is built around.

---

RULE: progress-report-cadence
CITE: 34 CFR §300.320(a)(3)
PLAIN: The IEP must include a description of how the child's progress toward meeting annual
       goals will be measured, and when periodic progress reports will be provided.
DERIVES: A calendar entry per student per goal: next progress-report due date, derived from
         the cadence stated in IEPRecord.goals[].progress_cadence. Feeds Family 2 and the
         reconciliation module's "stale goal" finding (cx/05) when a report is overdue.

---

RULE: annual-goals-basis
CITE: 34 CFR §300.320(a)(2)
PLAIN: The IEP must include a statement of measurable annual goals, including academic and
       functional goals, designed to meet the child's needs resulting from the disability.
DERIVES: Not a standalone Obligation-generating rule — this is the citation backing why
         IEPRecord.goals[] exist as first-class extracted objects at all, referenced by
         progress-report-cadence and by cx/05's goal-mapping logic.

---

RULE: services-statement
CITE: 34 CFR §300.320(a)(4)
PLAIN: The IEP must include a statement of the special education and related services,
       supplementary aids and services, and program modifications to be provided, based on
       peer-reviewed research to the extent practicable.
DERIVES: Backs why IEPRecord.services[] (with minutes_per_week, frequency, provider_role)
         exist as extracted objects, and is the citation basis for Family 3's service-minute
         accounting — a service's mandated minutes trace to this clause.

---

RULE: iep-in-effect-start-of-year
CITE: 34 CFR §300.323(a)
PLAIN: At the beginning of each school year, the public agency must have an IEP in effect for
       each child with a disability within its jurisdiction.
DERIVES: A baseline Finding if a student in the roster has no approved (is_current_approved)
         IEP record on file at school-year start — a foundational implementation-gap check
         underlying Family 4.

---

RULE: triennial-reevaluation
CITE: 34 CFR §300.303(b)(2) [cite as commonly stated; verify literal text yourself]
PLAIN: A reevaluation must occur at least once every 3 years, unless the parent and the
       public agency agree that a reevaluation is unnecessary.
DERIVES: A calendar entry per student: triennial_reeval deadline = last evaluation date + 3
         years. 30/14/3-day lead-time warnings, same pattern as annual-review.
ACTION REQUIRED: Fetch the live text of 34 CFR §300.303 (Cornell LII or eCFR) yourself,
confirm the exact subsection number and wording, then delete this warning line.

---

## Sources (fetched live, 2026-07-19)

- 34 CFR §300.323 (When IEPs must be in effect) — https://www.law.cornell.edu/cfr/text/34/300.323
- 34 CFR §300.320 (Definition of IEP) — https://www.law.cornell.edu/cfr/text/34/300.320
- 34 CFR §300.324 (Development, review, and revision of IEP) — https://www.law.cornell.edu/cfr/text/34/300.324
- §300.303 (Reevaluations) — NOT fetched this session; verify before use.

## What's deliberately out of scope for cx/02's rule families

- §300.323(e)/(f) — transfer-continuity rules (same-state / cross-state transfers). Real IDEA
  content, but no rule family in the branch file needs it yet. Don't build it speculatively.
- §300.324(a) IEP-development special-factors (behavior, LEP, Braille, communication needs) —
  relevant to authoring, which Bridgeline deliberately doesn't do. Out of scope by design.