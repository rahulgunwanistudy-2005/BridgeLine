import type { PipelineStatusEvent } from "../../lib/types/generated";

export const PIPELINE_STAGES = [
  { id: "ingest", label: "Ingest", eyebrow: "Prepare source" },
  { id: "extract", label: "Extract", eyebrow: "Structure evidence" },
  { id: "confidence_gate", label: "Confidence Gate", eyebrow: "Surface uncertainty" },
  { id: "human_approval", label: "Human Approval", eyebrow: "Verify legal truth" },
  { id: "rules", label: "Rules", eyebrow: "Derive duties" },
] as const;

export type StreamConnectionState = "connecting" | "live" | "paused" | "complete" | "reconnecting" | "error";

export interface PipelineViewModel {
  stages: Map<string, PipelineStatusEvent>;
  childLanes: Map<string, PipelineStatusEvent[]>;
  latest: PipelineStatusEvent | null;
}

export function canonicalEvents(events: readonly PipelineStatusEvent[]): PipelineStatusEvent[] {
  const bySequence = new Map<number, PipelineStatusEvent>();
  for (const event of events) {
    bySequence.set(event.seq, event);
  }
  return [...bySequence.values()].sort((left, right) => left.seq - right.seq);
}

export function buildPipelineViewModel(events: readonly PipelineStatusEvent[]): PipelineViewModel {
  const ordered = canonicalEvents(events);
  const stages = new Map<string, PipelineStatusEvent>();
  const children = new Map<string, Map<string, PipelineStatusEvent>>();
  for (const event of ordered) {
    if (event.parent_stage === null) {
      stages.set(event.stage, event);
      continue;
    }
    const group = children.get(event.parent_stage) ?? new Map<string, PipelineStatusEvent>();
    group.set(event.stage, event);
    children.set(event.parent_stage, group);
  }
  return {
    stages,
    childLanes: new Map(
      [...children.entries()].map(([parent, group]) => [
        parent,
        [...group.values()].sort((left, right) => left.seq - right.seq),
      ]),
    ),
    latest: ordered.at(-1) ?? null,
  };
}

export function isPipelinePaused(event: PipelineStatusEvent | null): boolean {
  return event?.stage === "human_approval" && event.state === "needs_review";
}

export function isPipelineComplete(event: PipelineStatusEvent | null): boolean {
  return event?.stage === "rules" && event.state === "done";
}
