import { describe, expect, it } from "vitest";

import { pipelineEvents } from "../../../mock/fixtures";
import { buildPipelineViewModel, canonicalEvents } from "./pipeline-model";

describe("pipeline view model", () => {
  it("keeps the latest event for each stage and preserves fan-out lanes", () => {
    const model = buildPipelineViewModel(pipelineEvents);
    expect(model.stages.get("ingest")?.state).toBe("done");
    expect(model.childLanes.get("ingest")).toHaveLength(2);
    expect(model.latest?.seq).toBe(12);
  });

  it("deduplicates replayed sequences into canonical order", () => {
    const result = canonicalEvents([pipelineEvents[2]!, pipelineEvents[0]!, pipelineEvents[2]!]);
    expect(result.map((event) => event.seq)).toEqual([1, 3]);
  });
});
