/* Generated from packages/schemas. Do not edit by hand. */

export type Obligation = {
  [k: string]: unknown;
} & {
  /**
   * Stable UUID identifying this derived teacher obligation across regeneration when its source accommodation and assignment are unchanged.
   */
  id: string;
  /**
   * District identifier for the student whose approved accommodation creates this obligation.
   */
  student_ref: string;
  /**
   * Kind of approved IEP source from which the obligation was derived.
   */
  source_kind: "iep_record" | "accommodation" | "service";
  /**
   * Stable UUID of the approved IEP version, accommodation, or service identified by source_kind.
   */
  source_ref: string;
  /**
   * Exact approved scope references that caused this obligation. Empty only for obligations sourced from an IEP record or service rather than an accommodation.
   */
  scope_provenance: ObligationScopeProvenance[];
  /**
   * Stable identifier of the deterministic rule that distributed or transformed the source accommodation into this obligation.
   */
  rule_id: string;
  /**
   * Legal or policy citation supporting the deterministic rule and rendered for reviewer verification.
   */
  citation: string;
  /**
   * Mandatory teacher action produced exclusively by the deterministic rules engine and never authored or altered by an LLM.
   */
  action_text: string;
  /**
   * Optional subject-specific implementation guidance authored later by the LLM, or null before brief generation.
   */
  practice_text: string | null;
  /**
   * Teacher workflow state indicating whether the obligation awaits action, has been confirmed, or has been flagged for resolution.
   */
  status: "pending" | "confirmed" | "flagged";
  /**
   * UTC RFC 3339 confirmation timestamp ending in Z when status is confirmed, otherwise null.
   */
  confirmed_at: string | null;
  /**
   * Teacher-provided explanation when status is flagged, otherwise null.
   */
  flag_reason: string | null;
};

/**
 * Deterministically derived legal implementation obligations grouped by responsible assignee and implementation context.
 */
export interface ObligationSet {
  /**
   * Kind of person responsible for the obligations in this set.
   */
  assignee_kind: "teacher" | "provider";
  /**
   * District identifier for the teacher or provider responsible for this set.
   */
  assignee_ref: string;
  /**
   * Human-readable implementation role of the responsible assignee.
   */
  assignee_role: string;
  /**
   * Kind of implementation context shared by the obligations in this set.
   */
  context_kind: "student" | "class" | "service";
  /**
   * Stable district or domain identifier for the implementation context.
   */
  context_ref: string;
  /**
   * Instructional subject for a class context, or null for student and service contexts.
   */
  subject: string | null;
  /**
   * UTC RFC 3339 timestamp ending in Z when the deterministic obligation set was generated.
   */
  generated_at: string;
  /**
   * Immutable version identifier of the deterministic rule registry used to derive these obligations.
   */
  rules_version: string;
  /**
   * Individual implementation requirements traceable to stable accommodations and cited deterministic rules.
   */
  obligations: Obligation[];
}
export interface ObligationScopeProvenance {
  /**
   * Applicability dimension that contributed to this obligation.
   */
  scope: "subject" | "context" | "all";
  /**
   * Scope name or phrase copied from the approved IEPRecord.
   */
  ref: string;
  /**
   * One-based source page supporting this scope.
   */
  source_page: number;
  /**
   * Verbatim source excerpt supporting this scope.
   */
  source_quote: string;
  /**
   * Approved extraction confidence for this scope reference.
   */
  confidence: number;
}
