/* Generated from packages/schemas. Do not edit by hand. */

/**
 * Normalized numeric or textual observation, with application validation requiring exactly one populated value.
 */
export type Measurement = {
  /**
   * Stable metric label such as assignment_percentage, rubric_score, minutes_delivered, or teacher_narrative.
   */
  metric: string;
  /**
   * Normalized quantitative value when the source is numeric, otherwise null.
   */
  numeric_value: number | null;
  /**
   * Normalized narrative value when the source is textual, otherwise null.
   */
  text_value: string | null;
  /**
   * Unit for a numeric measurement, such as percent, points, or minutes, otherwise null when not applicable.
   */
  unit: string | null;
} & (
  | {
      numeric_value?: number;
      text_value?: null;
    }
  | {
      numeric_value?: null;
      text_value?: string;
    }
);

/**
 * Normalized, source-linked observation used to reconcile classroom evidence, service delivery, and IEP goal progress.
 */
export interface ProgressSignal {
  /**
   * UUID identifying this normalized progress observation across reconciliation and audit workflows.
   */
  signal_id: string;
  /**
   * District identifier for the student to whom this progress observation belongs.
   */
  student_ref: string;
  /**
   * Controlled category identifying whether the observation came from achievement data, delivered service minutes, or teacher narrative.
   */
  signal_type: "grade" | "service_minutes" | "teacher_check_in";
  /**
   * UTC RFC 3339 timestamp ending in Z representing when the underlying performance or service was observed.
   */
  observed_at: string;
  /**
   * UTC RFC 3339 timestamp ending in Z representing when Bridgeline normalized the source record.
   */
  ingested_at: string;
  recorded_by: SignalActor;
  measurement: Measurement;
  source: SignalSource;
  goal_mapping: GoalMapping;
}
/**
 * Human or system actor responsible for recording the underlying observation.
 */
export interface SignalActor {
  /**
   * District identifier of the responsible human, or the literal system identifier for automated imports.
   */
  actor_ref: string;
  /**
   * Role under which the actor recorded or supplied the progress observation.
   */
  actor_role: "teacher" | "provider" | "case_manager" | "system";
}
/**
 * Traceable evidence locator for the original row, entry, or check-in from which the signal was normalized.
 */
export interface SignalSource {
  /**
   * Human-readable file, form, or source-system name from which the progress observation originated.
   */
  source_name: string;
  /**
   * Stable row, entry, or record identifier that permits retrieval of the original evidence.
   */
  source_record_ref: string;
  /**
   * Raw source excerpt supporting the normalized measurement and displayed during reconciliation review.
   */
  source_excerpt: string;
}
/**
 * Reviewable mapping between this signal and an IEP goal, including confidence and rationale when mapped.
 */
export interface GoalMapping {
  /**
   * Stable UUID of the mapped IEP goal, or null while the signal is unmapped.
   */
  goal_id: string | null;
  /**
   * Workflow state describing whether goal linkage is absent, automated, human-confirmed, or ambiguous.
   */
  status: "unmapped" | "auto_mapped" | "confirmed" | "needs_review";
  /**
   * Mapping confidence from 0.0 to 1.0 when a goal link has been proposed, otherwise null.
   */
  confidence: number | null;
  /**
   * Evidence-based explanation for the proposed or confirmed goal mapping, otherwise null when unmapped.
   */
  rationale: string | null;
}
