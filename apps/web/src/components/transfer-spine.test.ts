import { describe, expect, it } from "vitest";

import { initialTransferStage, transferStages } from "./TransferSpine";

describe("obligation transfer spine", () => {
  it("opens on the complete, static transformation when reduced motion is preferred", () => {
    expect(initialTransferStage(true)).toBe("confirm");
  });

  it("keeps a stable narrative order for landing and Judge Mode", () => {
    expect(transferStages).toEqual(["source", "evidence", "verify", "cite", "deliver", "confirm"]);
    expect(initialTransferStage(false)).toBe("source");
  });
});
