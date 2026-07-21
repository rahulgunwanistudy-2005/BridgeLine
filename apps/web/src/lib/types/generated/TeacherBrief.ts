/* Generated from packages/schemas. Do not edit by hand. */

/**
 * Authorized one-class teacher brief that preserves deterministic obligations while adding source-grounded implementation guidance.
 */
export interface TeacherBrief {
  /**
   * UUID identifying this teacher brief for delivery, confirmation, flagging, and audit events.
   */
  brief_id: string;
  /**
   * District identifier of the teacher authorized to receive this brief.
   */
  teacher_ref: string;
  /**
   * District or SIS identifier of the class to which every item in this brief applies.
   */
  class_ref: string;
  /**
   * Instructional subject used to contextualize practice guidance without altering mandatory actions.
   */
  subject: string;
  /**
   * School year for this brief in YYYY-YYYY form, with application validation requiring consecutive years.
   */
  school_year: string;
  /**
   * UTC RFC 3339 timestamp ending in Z when this brief payload was generated.
   */
  generated_at: string;
  /**
   * Immutable rule-registry version that produced the mandatory actions included in the brief.
   */
  rules_version: string;
  /**
   * Lifecycle state showing whether the brief is awaiting release, available to the teacher, confirmed, or flagged.
   */
  status: "draft" | "released" | "confirmed" | "flagged";
  /**
   * UTC RFC 3339 release timestamp ending in Z once a case manager releases the brief, otherwise null.
   */
  released_at: string | null;
  /**
   * UTC RFC 3339 timestamp ending in Z when the teacher confirms the brief, otherwise null.
   */
  confirmed_at: string | null;
  /**
   * Teacher-provided explanation when the brief is flagged, otherwise null.
   */
  flag_reason: string | null;
  responsibility: Responsibility;
  /**
   * Authorized student sections containing only the implementation information needed for this class.
   */
  students: StudentBrief[];
}
/**
 * Plain-language statement of the teacher's implementation responsibility together with its legal citation.
 */
export interface Responsibility {
  /**
   * Actionable statement explaining the teacher's duty to provide the listed accommodations and supports.
   */
  text: string;
  /**
   * Legal citation supporting the responsibility statement, normally IDEA 34 CFR section 300.323(d).
   */
  citation: string;
}
export interface StudentBrief {
  /**
   * District identifier of the student whose approved obligations are shown in this authorized class brief.
   */
  student_ref: string;
  /**
   * Authorized display name used by the teacher to identify the student in this class.
   */
  student_name: string;
  /**
   * Mandatory actions and contextual practice guidance for this student, each retaining complete source and rule traceability.
   */
  obligations: BriefObligation[];
}
export interface BriefObligation {
  /**
   * UUID of the deterministic obligation represented by this brief item.
   */
  obligation_id: string;
  /**
   * Stable UUID of the source accommodation, preserved across IEP re-extractions through reconciliation.
   */
  accommodation_id: string;
  /**
   * Exact approved accommodation language from the reviewed IEP record.
   */
  accommodation_text: string;
  /**
   * Mandatory action copied unchanged from the deterministic obligation and protected from LLM modification.
   */
  action_text: string;
  /**
   * LLM-authored subject-specific guidance explaining a practical way to implement the mandatory action.
   */
  practice_text: string;
  /**
   * One-based IEP source page supporting the accommodation shown in this brief item.
   */
  source_page: number;
  /**
   * Verbatim IEP excerpt supporting the accommodation shown in this brief item.
   */
  source_quote: string;
  /**
   * Approved extraction confidence from 0.0 to 1.0 inherited from the source accommodation.
   */
  source_confidence: number;
  /**
   * Identifier of the deterministic rule that produced the mandatory action.
   */
  rule_id: string;
  /**
   * Legal or policy citation supporting the deterministic obligation.
   */
  citation: string;
}
