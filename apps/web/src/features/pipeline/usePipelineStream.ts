import { useCallback, useEffect, useRef, useState } from "react";

import { apiClient } from "../../lib/api/client";
import type { PipelineStatusEvent } from "../../lib/types/generated";
import {
  canonicalEvents,
  isPipelineComplete,
  isPipelinePaused,
  type StreamConnectionState,
} from "./pipeline-model";

interface StoredRunState {
  runId: string;
  events: PipelineStatusEvent[];
}

interface PipelineStreamResult {
  events: PipelineStatusEvent[];
  connectionState: StreamConnectionState;
  error: string | null;
  reconnect: () => void;
}

export function usePipelineStream(runId: string): PipelineStreamResult {
  const initial = readStoredState(runId);
  const [events, setEvents] = useState<PipelineStatusEvent[]>(initial);
  const [connectionState, setConnectionState] = useState<StreamConnectionState>("connecting");
  const [error, setError] = useState<string | null>(null);
  const [generation, setGeneration] = useState(0);
  const eventsRef = useRef(events);
  eventsRef.current = events;

  const reconnect = useCallback(() => {
    setError(null);
    setConnectionState("reconnecting");
    setGeneration((current) => current + 1);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    const cursor = eventsRef.current.at(-1)?.seq;
    setConnectionState(cursor === undefined ? "connecting" : "live");

    void apiClient
      .streamPipeline(runId, {
        ...(cursor === undefined ? {} : { lastEventId: cursor }),
        signal: controller.signal,
        onEvent: (event) => {
          if (!active) return;
          setConnectionState("live");
          setEvents((current) => {
            const next = canonicalEvents([...current, event]);
            storeRunState(runId, next);
            return next;
          });
        },
      })
      .then(() => {
        if (!active) return;
        const latest = eventsRef.current.at(-1) ?? null;
        if (isPipelinePaused(latest)) setConnectionState("paused");
        else if (isPipelineComplete(latest)) setConnectionState("complete");
        else setConnectionState("reconnecting");
      })
      .catch((reason: unknown) => {
        if (!active || controller.signal.aborted) return;
        setError(reason instanceof Error ? reason.message : "The live pipeline connection closed.");
        setConnectionState("error");
      });

    return () => {
      active = false;
      controller.abort();
    };
  }, [generation, runId]);

  return { events, connectionState, error, reconnect };
}

function readStoredState(runId: string): PipelineStatusEvent[] {
  const state = window.history.state as { bridgelineRun?: StoredRunState } | null;
  return state?.bridgelineRun?.runId === runId ? state.bridgelineRun.events : [];
}

function storeRunState(runId: string, events: PipelineStatusEvent[]): void {
  const current = (window.history.state as Record<string, unknown> | null) ?? {};
  window.history.replaceState({ ...current, bridgelineRun: { runId, events } }, "");
}
