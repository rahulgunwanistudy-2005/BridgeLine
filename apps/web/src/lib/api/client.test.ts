import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";

import { MOCK_RUN_ID, pipelineEvents, teacherBrief } from "../../../mock/fixtures";
import { mockServer } from "../../../mock/server";
import { resetMockState } from "../../../mock/handlers";
import { BridgelineApiClient } from "./client";

const client = new BridgelineApiClient("http://localhost:8000");

beforeAll(() => mockServer.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  mockServer.resetHandlers();
  resetMockState();
});
afterAll(() => mockServer.close());

describe("Riverside mock API", () => {
  it("streams the complete scripted pipeline in sequence", async () => {
    const received: number[] = [];
    await client.streamPipeline(MOCK_RUN_ID, {
      onEvent: (event) => received.push(event.seq),
    });
    expect(received).toEqual(pipelineEvents.slice(0, 9).map((event) => event.seq));
  });

  it("resumes strictly after Last-Event-ID", async () => {
    await client.approveRun(MOCK_RUN_ID, "demo-case-manager");
    const received: number[] = [];
    await client.streamPipeline(MOCK_RUN_ID, {
      lastEventId: 8,
      onEvent: (event) => received.push(event.seq),
    });
    expect(received).toEqual([9, 10, 11, 12]);
  });

  it("serves the three deterministic Riverside findings", async () => {
    const result = await client.findings();
    expect(result).toHaveLength(3);
    expect(result[0]?.title).toBe("Extended time — confirmed in 3 of 6 classes");
  });

  it("serves and confirms the schema-valid Renata Delgado brief", async () => {
    const result = await client.teacherBriefs("T-DELGADO");
    expect(result[0]?.brief_id).toBe(teacherBrief.brief_id);
    const confirmed = await client.confirmBrief(teacherBrief.brief_id);
    expect(confirmed.status).toBe("confirmed");
    expect(confirmed.confirmed_at).not.toBeNull();
  });

  it("preserves the teacher-provided flag reason", async () => {
    const flagged = await client.flagBrief(teacherBrief.brief_id, "The testing room is unavailable.");
    expect(flagged.status).toBe("flagged");
    expect(flagged.flag_reason).toBe("The testing room is unavailable.");
  });
});
