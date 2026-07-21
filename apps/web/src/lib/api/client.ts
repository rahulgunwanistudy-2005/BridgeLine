import { webConfig } from "../env";
import type {
  ApprovalResponse,
  Deadline,
  Finding,
  FindingStatus,
  HealthResponse,
  PipelineRunResponse,
  PipelineStreamOptions,
  RegistryResponse,
  UploadResponse,
} from "./contracts";
import { consumePipelineEvents } from "./sse";
import type { TeacherBrief } from "../types/generated";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export class BridgelineApiClient {
  constructor(private readonly baseUrl: string) {}

  health(): Promise<HealthResponse> {
    return this.request("/health");
  }

  upload(file: File, lineageHint?: string): Promise<UploadResponse> {
    const body = new FormData();
    body.set("file", file);
    if (lineageHint !== undefined) {
      body.set("lineage_hint", lineageHint);
    }
    return this.request("/ieps/upload", { method: "POST", body });
  }

  pipelineRun(runId: string): Promise<PipelineRunResponse> {
    return this.request(`/pipeline/${runId}`);
  }

  approveRun(runId: string, actorRef: string): Promise<ApprovalResponse> {
    return this.request(`/pipeline/${runId}/approve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ actor_ref: actorRef }),
    });
  }

  findings(): Promise<Finding[]> {
    return this.request("/findings");
  }

  deriveFindings(): Promise<Finding[]> {
    return this.request("/findings/derive", { method: "POST" });
  }

  transitionFinding(id: string, status: FindingStatus): Promise<Finding> {
    return this.request(`/findings/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status, actor_ref: "demo-case-manager", actor_role: "case_manager" }),
    });
  }

  rules(): Promise<RegistryResponse> {
    return this.request("/rules");
  }

  deadlines(): Promise<Deadline[]> {
    return this.request("/compliance/deadlines");
  }

  teacherBriefs(teacherId: string): Promise<TeacherBrief[]> {
    return this.request(`/teachers/${teacherId}/briefs`);
  }

  confirmBrief(briefId: string): Promise<TeacherBrief> {
    return this.request(`/briefs/${briefId}/confirm`, { method: "POST" });
  }

  flagBrief(briefId: string, reason: string): Promise<TeacherBrief> {
    return this.request(`/briefs/${briefId}/flag`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reason }),
    });
  }

  async streamPipeline(runId: string, options: PipelineStreamOptions): Promise<void> {
    const headers = new Headers({ Accept: "text/event-stream" });
    if (options.lastEventId !== undefined) {
      headers.set("Last-Event-ID", String(options.lastEventId));
    }
    const init: RequestInit = { headers };
    if (options.signal !== undefined) {
      init.signal = options.signal;
    }
    const response = await fetch(this.url(`/pipeline/${runId}/events`), init);
    await consumePipelineEvents(response, options.onEvent);
  }

  private async request<T>(path: string, init?: RequestInit): Promise<T> {
    const response = await fetch(this.url(path), init);
    if (!response.ok) {
      const detail = await response.text();
      throw new ApiError(detail || `Request failed with HTTP ${response.status}.`, response.status);
    }
    return (await response.json()) as T;
  }

  private url(path: string): string {
    return new URL(path, `${this.baseUrl.replace(/\/$/, "")}/`).toString();
  }
}

export const apiClient = new BridgelineApiClient(webConfig.apiBaseUrl);
