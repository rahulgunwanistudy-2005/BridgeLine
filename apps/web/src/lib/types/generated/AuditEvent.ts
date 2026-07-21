/* Generated from packages/schemas. Do not edit by hand. */

/**
 * JSON-compatible scalar, array, object, or null retained as the exact audited field value.
 */
export type NullableJsonValue =
  | string
  | number
  | boolean
  | NullableJsonValue[]
  | {
      [k: string]: NullableJsonValue;
    }
  | null;

/**
 * Immutable record of a consequential Bridgeline action with actor, timestamp, changed values, and supporting evidence.
 */
export interface AuditEvent {
  /**
   * UUID uniquely identifying this append-only audit event.
   */
  event_id: string;
  /**
   * Lowercase dotted action name, such as iep.approved or brief.confirmed, used for typed event routing.
   */
  event_type: string;
  /**
   * UTC RFC 3339 timestamp ending in Z when the audited action occurred.
   */
  occurred_at: string;
  /**
   * Human-readable factual summary of the action suitable for the compliance timeline.
   */
  summary: string;
  actor: AuditActor;
  subject: AuditSubject;
  /**
   * Field-level before-and-after values needed to reconstruct what changed without mutating prior events.
   */
  changes: AuditChange[];
  /**
   * Source records and citations that substantiate the audited action or state transition.
   */
  evidence: EvidenceReference[];
  /**
   * UUID grouping multiple audit events produced by one user operation, or null when no grouping applies.
   */
  correlation_id: string | null;
  /**
   * Pipeline run UUID that caused this action, or null for actions outside a pipeline run.
   */
  run_id: string | null;
}
/**
 * Human or system identity responsible for the audited action.
 */
export interface AuditActor {
  /**
   * District identifier of the responsible human, or the literal system identity for automated actions.
   */
  actor_ref: string;
  /**
   * Authorized role under which the actor performed the audited action.
   */
  actor_role: "case_manager" | "compliance_admin" | "teacher" | "provider" | "system";
}
/**
 * Primary domain record affected by the audited action.
 */
export interface AuditSubject {
  /**
   * Domain type of the affected record, such as iep_record, obligation, brief, or pipeline_run.
   */
  subject_type: string;
  /**
   * Stable identifier of the affected domain record.
   */
  subject_ref: string;
}
export interface AuditChange {
  /**
   * JSON-path-like location of the field affected by this change.
   */
  field_path: string;
  /**
   * Typed JSON value before the action, or null when the field did not previously exist.
   */
  previous_value:
    | string
    | number
    | boolean
    | NullableJsonValue[]
    | {
        [k: string]: NullableJsonValue;
      }
    | null;
  /**
   * JSON-compatible scalar, array, object, or null retained as the exact audited field value.
   */
  new_value:
    | string
    | number
    | boolean
    | NullableJsonValue[]
    | {
        [k: string]: NullableJsonValue;
      }
    | null;
}
export interface EvidenceReference {
  /**
   * Controlled category identifying the kind of evidence that supports the audited action.
   */
  evidence_type: "iep_source" | "rule_citation" | "progress_signal" | "document" | "audit_event";
  /**
   * Stable identifier or citation key used to retrieve the supporting evidence.
   */
  evidence_ref: string;
  /**
   * Page, row, section, or other precise location within the evidence, or null when the reference is already exact.
   */
  locator: string | null;
}
