import addFormats from "ajv-formats";
import Ajv2020 from "ajv/dist/2020";
import { describe, expect, it } from "vitest";

import iepSchema from "../../../packages/schemas/IEPRecord.json";
import pipelineEventSchema from "../../../packages/schemas/PipelineStatusEvent.json";
import teacherBriefSchema from "../../../packages/schemas/TeacherBrief.json";
import { pipelineEvents, registry, riversideRecord, teacherBrief } from "./fixtures";

const ajv = new Ajv2020({ allErrors: true, strict: true });
addFormats(ajv);
const validateIep = ajv.compile(iepSchema);
const validatePipelineEvent = ajv.compile(pipelineEventSchema);
const validateTeacherBrief = ajv.compile(teacherBriefSchema);

describe("schema-valid Riverside fixtures", () => {
  it("uses an unmodified ground-truth IEPRecord", () => {
    expect(validateIep(riversideRecord), JSON.stringify(validateIep.errors)).toBe(true);
  });

  it("validates every scripted SSE event against PipelineStatusEvent", () => {
    for (const event of pipelineEvents) {
      expect(validatePipelineEvent(event), JSON.stringify(validatePipelineEvent.errors)).toBe(true);
    }
  });

  it("pulls the complete exact registry from generated RULES.md content", () => {
    expect(registry.rules).toHaveLength(10);
    expect(registry.rules[2]?.citation).toBe("34 CFR §300.323(d)(2)(ii)");
  });

  it("validates the teacher brief and preserves exact Riverside source text", () => {
    expect(validateTeacherBrief(teacherBrief), JSON.stringify(validateTeacherBrief.errors)).toBe(true);
    expect(teacherBrief.students[0]?.obligations[0]?.source_quote).toBe(
      riversideRecord.accommodations[0]?.source_quote,
    );
  });
});
