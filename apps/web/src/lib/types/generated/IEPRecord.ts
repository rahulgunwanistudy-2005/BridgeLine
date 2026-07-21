/* Generated from packages/schemas. Do not edit by hand. */

/**
 * Canonical, source-grounded extraction of one physical IEP document within a stable record lineage.
 */
export interface IEPRecord {
  /**
   * Stable UUID for this physical IEP lineage; it is preserved when the same IEP is extracted again and differs from the per-run extraction identifier.
   */
  iep_record_id: string;
  /**
   * District or SIS identifier for the student whose IEP was extracted; this external reference is not required to be a UUID.
   */
  student_ref: string;
  /**
   * Eligibility or disability category stated in the approved IEP, preserved as document language rather than inferred by the system.
   */
  disability_category: string;
  /**
   * School year covered by the IEP in YYYY-YYYY form, with application validation requiring consecutive years.
   */
  school_year: string;
  /**
   * Approved accommodations extracted from the IEP, each with a stable identity and mandatory source evidence.
   */
  accommodations: Accommodation[];
  /**
   * Mandated services extracted from the IEP, including delivery schedule and mandatory source evidence.
   */
  services: Service[];
  /**
   * Measurable annual goals extracted from the IEP, including progress criteria and mandatory source evidence.
   */
  goals: Goal[];
  dates: IEPDates;
  field_confidences: FieldConfidences;
  extraction_meta: ExtractionMeta;
}
export interface Accommodation {
  /**
   * Stable UUID carried forward by reconciliation when this accommodation reappears in a later extraction of the same IEP.
   */
  id: string;
  /**
   * Exact approved accommodation language, normalized only enough to remove extraction artifacts without changing meaning.
   */
  text: string;
  /**
   * Source-grounded applicability references. References within one scope are alternatives; subject and context scopes combine by intersection. An all reference is exclusive and means no subject or context constraint.
   */
  applies_to_refs: AccommodationScopeReference[];
  /**
   * One-based page number containing the evidence for this accommodation in the normalized source document.
   */
  source_page: number;
  /**
   * Verbatim source excerpt that supports the extracted accommodation and is shown during human review.
   */
  source_quote: string;
  /**
   * Extraction confidence from 0.0 to 1.0 for this accommodation, used by the confidence gate and evaluation harness.
   */
  confidence: number;
  /**
   * Identity-reconciliation result against the prior approved extraction: matched preserves a prior ID, new allocates a new stable ID, ambiguous requires human resolution, and null is reserved for the first extraction in an IEP lineage.
   */
  reconciliation_status: "matched" | "new" | "ambiguous" | null;
}
export interface AccommodationScopeReference {
  /**
   * Applicability dimension stated in the IEP. References within one scope are alternatives, subject and context scopes combine by intersection, and all is exclusive.
   */
  scope: "subject" | "context" | "all";
  /**
   * Scope name or phrase as stated in the document, such as Mathematics, during testing, or across all classes. Never a district identifier.
   */
  ref: string;
  /**
   * One-based page number containing the evidence for this scope reference.
   */
  source_page: number;
  /**
   * Verbatim source excerpt supporting this scope reference.
   */
  source_quote: string;
  /**
   * Extraction confidence from 0.0 to 1.0 for this scope reference.
   */
  confidence: number;
}
export interface Service {
  /**
   * Stable UUID carried forward by reconciliation when this service reappears in a later extraction of the same IEP.
   */
  id: string;
  /**
   * Type of mandated special-education or related service stated in the IEP.
   */
  type: string;
  /**
   * Total number of service minutes mandated per week, normalized for deterministic compliance accounting.
   */
  minutes_per_week: number;
  /**
   * Service frequency or schedule language stated in the IEP, retained for reviewer verification.
   */
  frequency: string;
  /**
   * Role responsible for delivering the service, such as speech-language pathologist or special educator.
   */
  provider_role: string;
  /**
   * School-local YYYY-MM-DD date on which service delivery begins, or null when the source does not provide a reliable date.
   */
  start: string | null;
  /**
   * School-local YYYY-MM-DD date on which service delivery ends, or null when the source does not provide a reliable date.
   */
  end: string | null;
  /**
   * One-based page number containing the evidence for this mandated service.
   */
  source_page: number;
  /**
   * Verbatim source excerpt supporting the service type, schedule, minutes, and provider assignment.
   */
  source_quote: string;
  /**
   * Extraction confidence from 0.0 to 1.0 for this service, used by the confidence gate and evaluation harness.
   */
  confidence: number;
  /**
   * Identity-reconciliation result against the prior approved extraction: matched preserves a prior ID, new allocates a new stable ID, ambiguous requires human resolution, and null is reserved for the first extraction in an IEP lineage.
   */
  reconciliation_status: "matched" | "new" | "ambiguous" | null;
}
export interface Goal {
  /**
   * Stable UUID carried forward by reconciliation when this goal reappears in a later extraction of the same IEP.
   */
  id: string;
  /**
   * Complete measurable annual goal language as approved in the IEP.
   */
  text: string;
  /**
   * Present level or starting performance against which progress toward this goal is measured.
   */
  baseline: string;
  /**
   * Expected performance threshold or outcome that constitutes attainment of the goal.
   */
  target: string;
  /**
   * Assessment, observation, work sample, or other method specified for measuring progress.
   */
  measure: string;
  /**
   * Required frequency for collecting or reporting progress evidence for this goal.
   */
  progress_cadence: string;
  /**
   * One-based page number containing the evidence for this annual goal.
   */
  source_page: number;
  /**
   * Verbatim source excerpt supporting the goal, baseline, target, measure, and cadence.
   */
  source_quote: string;
  /**
   * Extraction confidence from 0.0 to 1.0 for this goal, used by the confidence gate and evaluation harness.
   */
  confidence: number;
  /**
   * Identity-reconciliation result against the prior approved extraction: matched preserves a prior ID, new allocates a new stable ID, ambiguous requires human resolution, and null is reserved for the first extraction in an IEP lineage.
   */
  reconciliation_status: "matched" | "new" | "ambiguous" | null;
}
/**
 * School-local compliance dates represented without times so timezone conversion cannot change a legal deadline.
 */
export interface IEPDates {
  /**
   * School-local YYYY-MM-DD annual-review deadline, or null when reliable source evidence is unavailable.
   */
  annual_review: string | null;
  /**
   * School-local YYYY-MM-DD triennial-reevaluation deadline, or null when reliable source evidence is unavailable.
   */
  triennial_reeval: string | null;
  /**
   * School-local YYYY-MM-DD date of the most recent documented progress report, or null when none is available.
   */
  last_progress_report: string | null;
}
/**
 * Extraction confidence for canonical scalar and date fields that do not carry item-level confidence.
 */
export interface FieldConfidences {
  /**
   * Extraction confidence for student_ref; 0.0 required when the value is absent or unreliable.
   */
  student_ref: number;
  /**
   * Extraction confidence for disability_category; 0.0 required when the value is absent or unreliable.
   */
  disability_category: number;
  /**
   * Extraction confidence for school_year; 0.0 required when the value is absent or unreliable.
   */
  school_year: number;
  /**
   * Extraction confidence for annual_review; 0.0 required when the value is absent or unreliable.
   */
  annual_review: number;
  /**
   * Extraction confidence for triennial_reeval; 0.0 required when the value is absent or unreliable.
   */
  triennial_reeval: number;
  /**
   * Extraction confidence for last_progress_report; 0.0 required when the value is absent or unreliable.
   */
  last_progress_report: number;
}
/**
 * Provenance for this particular extraction run; these values may change while the IEP record identity remains stable.
 */
export interface ExtractionMeta {
  /**
   * Pinned model identifier used for the structured extraction, retained for reproducibility and audit.
   */
  model: string;
  /**
   * Unique identifier for this extraction attempt; unlike iep_record_id, it changes on every re-extraction.
   */
  run_id: string;
  /**
   * Number of normalized source pages processed during this extraction run.
   */
  page_count: number;
  /**
   * Per-page legibility scores from 0.0 to 1.0 in page order, with exactly one value for each source page.
   *
   * @minItems 1
   */
  legibility_scores: [number, ...number[]];
  /**
   * UTC RFC 3339 timestamp ending in Z when this extraction run completed.
   */
  extracted_at: string;
}
