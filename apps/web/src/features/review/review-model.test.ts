import { describe, expect, it } from "vitest";

import { riversideRecord } from "../../../mock/fixtures";
import { buildReviewFields, requiresReview } from "./review-model";

describe("source-grounded review model", () => {
  it("preserves every accommodation quote and scope reference unmodified", () => {
    const fields = buildReviewFields(riversideRecord).filter((field) => field.group === "Accommodations");
    expect(fields).toHaveLength(riversideRecord.accommodations.length);
    expect(fields[0]?.sourceQuote).toBe(riversideRecord.accommodations[0]?.source_quote);
    expect(fields[0]?.scopeReferences[0]?.ref).toBe("across all classes");
  });

  it("routes low-confidence values or scope references to review", () => {
    const fields = buildReviewFields(riversideRecord);
    expect(fields.filter((field) => requiresReview(field)).length).toBeGreaterThan(0);
  });

  it("does not invent source evidence for top-level confidence fields", () => {
    const student = buildReviewFields(riversideRecord).find((field) => field.key === "student_ref");
    expect(student?.sourcePage).toBeNull();
    expect(student?.sourceQuote).toBeNull();
  });
});
