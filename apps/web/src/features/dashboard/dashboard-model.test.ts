import { describe, expect, it } from "vitest";

import { deadlines, findings } from "../../../mock/fixtures";
import { groupFindings, orderedDeadlines } from "./dashboard-model";

describe("compliance dashboard model", () => {
  it("keeps the Riverside 3-of-6 finding unmistakable", () => {
    const gap = groupFindings(findings).implementationGaps[0];
    expect(gap?.title).toBe("Extended time — confirmed in 3 of 6 classes");
    expect(gap?.measurements).toEqual({ confirmed_classes: 3, total_classes: 6 });
  });

  it("places overdue deadlines before upcoming work", () => {
    expect(orderedDeadlines(deadlines).map((deadline) => deadline.status)).toEqual([
      "overdue", "overdue", "upcoming", "upcoming",
    ]);
  });

  it("separates service variance from implementation gaps", () => {
    const sections = groupFindings(findings);
    expect(sections.implementationGaps).toHaveLength(1);
    expect(sections.serviceVariances).toHaveLength(1);
    expect(sections.otherFindings).toHaveLength(1);
  });
});
