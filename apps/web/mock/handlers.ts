import { delay, http, HttpResponse } from "msw";

import type { Finding, FindingStatus } from "../src/lib/api/contracts";
import { webConfig } from "../src/lib/env";
import { deadlines, findings, MOCK_IEP_VERSION_ID, MOCK_RUN_ID, pipelineEvents, registry, teacherBrief } from "./fixtures";

const API_ROOT = webConfig.apiBaseUrl.replace(/\/$/, "");
let currentFindings = structuredClone(findings);
let currentTeacherBrief = structuredClone(teacherBrief);
let runApproved = false;

export const handlers = [
  http.get(`${API_ROOT}/health`, () => HttpResponse.json({ status: "ok", database: "ok" })),
  http.post(`${API_ROOT}/ieps/upload`, async () => {
    await delay(120);
    runApproved = false;
    return HttpResponse.json({ run_id: MOCK_RUN_ID }, { status: 202 });
  }),
  http.get(`${API_ROOT}/pipeline/:runId/events`, ({ request }) => {
    const lastEventId = Number(request.headers.get("Last-Event-ID") ?? "0");
    const replay = pipelineEvents.filter(
      (event) => event.seq > lastEventId && (runApproved || event.seq <= 9),
    );
    const encoder = new TextEncoder();
    const stream = new ReadableStream<Uint8Array>({
      async start(controller) {
        for (const event of replay) {
          controller.enqueue(encoder.encode(`id: ${event.seq}\ndata: ${JSON.stringify(event)}\n\n`));
          await delay(webConfig.isTestRuntime ? 1 : 420);
        }
        controller.close();
      },
    });
    return new HttpResponse(stream, {
      headers: { "Content-Type": "text/event-stream", "Cache-Control": "no-cache" },
    });
  }),
  http.get(`${API_ROOT}/pipeline/:runId`, () =>
    HttpResponse.json({
      run_id: MOCK_RUN_ID,
      state: runApproved ? "done" : "needs_review",
      current_stage: runApproved ? "rules" : "human_approval",
      detail: runApproved ? "Rules derivation complete." : "Awaiting case-manager approval.",
      attention: {
        kind: "human_approval",
        payload: { draft_id: MOCK_IEP_VERSION_ID, review_fields: ["accommodations.3"] },
        retryable: false,
      },
    }),
  ),
  http.post(`${API_ROOT}/pipeline/:runId/approve`, () => {
    const idempotent = runApproved;
    runApproved = true;
    return HttpResponse.json({
      run_id: MOCK_RUN_ID,
      iep_record_id: MOCK_IEP_VERSION_ID,
      state: "done",
      idempotent,
    });
  }),
  http.get(`${API_ROOT}/findings`, () => HttpResponse.json(currentFindings)),
  http.post(`${API_ROOT}/findings/derive`, () => HttpResponse.json(currentFindings)),
  http.patch(`${API_ROOT}/findings/:findingId`, async ({ params, request }) => {
    const payload = (await request.json()) as { status: FindingStatus };
    const found = currentFindings.find((finding) => finding.id === params.findingId);
    if (found === undefined) {
      return HttpResponse.json({ detail: "Finding not found" }, { status: 404 });
    }
    const updated: Finding = { ...found, status: payload.status };
    currentFindings = currentFindings.map((finding) =>
      finding.id === updated.id ? updated : finding,
    );
    return HttpResponse.json(updated);
  }),
  http.get(`${API_ROOT}/rules`, () => HttpResponse.json(registry)),
  http.get(`${API_ROOT}/compliance/deadlines`, () => HttpResponse.json(deadlines)),
  http.get(`${API_ROOT}/teachers/:teacherId/briefs`, ({ params }) =>
    HttpResponse.json(params.teacherId === currentTeacherBrief.teacher_ref ? [currentTeacherBrief] : []),
  ),
  http.post(`${API_ROOT}/briefs/:briefId/confirm`, ({ params }) => {
    if (params.briefId !== currentTeacherBrief.brief_id) {
      return HttpResponse.json({ detail: "Brief not found" }, { status: 404 });
    }
    currentTeacherBrief = {
      ...currentTeacherBrief,
      status: "confirmed",
      confirmed_at: "2026-11-13T16:07:00Z",
      flag_reason: null,
    };
    return HttpResponse.json(currentTeacherBrief);
  }),
  http.post(`${API_ROOT}/briefs/:briefId/flag`, async ({ params, request }) => {
    if (params.briefId !== currentTeacherBrief.brief_id) {
      return HttpResponse.json({ detail: "Brief not found" }, { status: 404 });
    }
    const payload = (await request.json()) as { reason?: string };
    if (payload.reason?.trim() === "") {
      return HttpResponse.json({ detail: "A reason is required" }, { status: 422 });
    }
    currentTeacherBrief = {
      ...currentTeacherBrief,
      status: "flagged",
      confirmed_at: null,
      flag_reason: payload.reason ?? "Teacher requested case-manager follow-up.",
    };
    return HttpResponse.json(currentTeacherBrief);
  }),
  http.get(`${API_ROOT}/ieps/:iepRecordId/obligations`, () => HttpResponse.json([])),
  http.post(`${API_ROOT}/ieps/:iepRecordId/obligations/derive`, () => HttpResponse.json([])),
];

export function resetMockState(): void {
  currentFindings = structuredClone(findings);
  currentTeacherBrief = structuredClone(teacherBrief);
  runApproved = false;
}
