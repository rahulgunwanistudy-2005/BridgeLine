/* Generated from packages/schemas. Do not edit by hand. */

/**
 * Persisted status event that is the sole data source for the resumable, human-readable pipeline visualization.
 */
export interface PipelineStatusEvent {
  /**
   * UUID of the pipeline run to which this event belongs.
   */
  run_id: string;
  /**
   * Strictly increasing sequence number within the run, used as the SSE Last-Event-ID resume cursor.
   */
  seq: number;
  /**
   * Stable machine-readable slug of the pipeline stage emitting this event.
   */
  stage: string;
  /**
   * Human-facing name of the agent or deterministic component displayed in the pipeline UI.
   */
  agent_label: string;
  /**
   * Controlled lifecycle state used by the UI to render stage status and human-review pauses.
   */
  state: "queued" | "running" | "done" | "needs_review" | "error";
  /**
   * User-facing explanation of what the stage is doing or why it needs attention; this is UX copy rather than an internal log line.
   */
  detail: string;
  /**
   * Fractional stage completion from 0.0 to 1.0, or null when meaningful progress cannot be calculated.
   */
  progress: number | null;
  /**
   * Machine-readable parent stage slug for a fan-out child lane, or null for a top-level stage.
   */
  parent_stage: string | null;
  /**
   * UTC RFC 3339 timestamp ending in Z when the event was persisted.
   */
  ts: string;
}
