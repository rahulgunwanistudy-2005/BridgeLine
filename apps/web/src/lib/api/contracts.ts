import type { IEPRecord, PipelineStatusEvent } from "../types/generated";

export type FindingStatus = "open" | "resolved";

export interface HealthResponse {
  status: "ok";
  database: "ok";
}

export interface UploadResponse {
  run_id: string;
}

export interface PipelineAttention {
  kind: string | null;
  payload: Record<string, unknown> | null;
  retryable: boolean;
}

export interface PipelineRunResponse {
  run_id: string;
  state: string;
  current_stage: string | null;
  detail: string;
  attention: PipelineAttention;
}

export interface ApprovalResponse {
  run_id: string;
  iep_record_id: string;
  state: string;
  idempotent: boolean;
}

export interface Finding {
  id: string;
  rule_id: string;
  citation: string;
  finding_type: string;
  severity: "info" | "warning" | "critical";
  student_ref: string;
  iep_record_version_id: string | null;
  detected_on: string;
  title: string;
  detail: string;
  related_refs: Record<string, unknown>;
  measurements: Record<string, unknown>;
  status: FindingStatus;
}

export interface RuleResponse {
  id: string;
  citation: string;
  description: string;
}

export interface RegistryResponse {
  rules_version: string;
  rules: RuleResponse[];
}

export interface Deadline {
  id: string;
  rule_id: string;
  citation: string;
  student_ref: string;
  iep_record_version_id: string;
  source_kind: "iep_record" | "accommodation" | "service";
  source_ref: string;
  legal_due_on: string;
  action_due_on: string;
  warning_30_on: string;
  warning_14_on: string;
  warning_3_on: string;
  status: "upcoming" | "due" | "overdue";
  description: string;
}

export interface PipelineStreamOptions {
  lastEventId?: number;
  signal?: AbortSignal;
  onEvent: (event: PipelineStatusEvent) => void;
}

export interface ReviewFixture {
  record: IEPRecord;
  sourceDocumentUrl: string;
}
