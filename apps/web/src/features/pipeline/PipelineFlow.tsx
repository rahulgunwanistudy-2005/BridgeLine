import { AlertTriangle, Check, Circle, Cog, Pause, RotateCw } from "lucide-react";

import type { PipelineStatusEvent } from "../../lib/types/generated";
import { buildPipelineViewModel, PIPELINE_STAGES } from "./pipeline-model";
import "./pipeline.css";

interface PipelineFlowProps {
  events: PipelineStatusEvent[];
}

const stateLabels: Record<PipelineStatusEvent["state"], string> = {
  queued: "Queued",
  running: "Running",
  done: "Done",
  needs_review: "Needs review",
  error: "Error",
};

export function PipelineFlow({ events }: PipelineFlowProps): React.JSX.Element {
  const model = buildPipelineViewModel(events);
  return (
    <ol aria-label="IEP processing stages" className="pipeline-flow">
      {PIPELINE_STAGES.map((definition, index) => {
        const event = model.stages.get(definition.id);
        const state = event?.state ?? "queued";
        const children = model.childLanes.get(definition.id) ?? [];
        return (
          <li className="pipeline-stage-wrap" key={definition.id}>
            <article className="pipeline-stage" data-state={state}>
              <div className="stage-index font-tabular">{String(index + 1).padStart(2, "0")}</div>
              <div className="stage-heading">
                <div>
                  <p>{definition.eyebrow}</p>
                  <h2>{event?.agent_label ?? definition.label}</h2>
                </div>
                <StageStateIcon state={state} />
              </div>
              <div className="stage-mechanism" aria-hidden="true">
                <span className="stage-notch" />
                <span className="stage-track" />
              </div>
              <p className="stage-detail">
                {event?.detail ?? `Waiting for ${definition.label.toLowerCase()}.`}
              </p>
              <div className="stage-meta">
                <span>{stateLabels[state]}</span>
                {event?.progress !== null && event?.progress !== undefined ? (
                  <span className="font-tabular">{Math.round(event.progress * 100)}%</span>
                ) : null}
              </div>
              {children.length > 0 ? <ParallelLanes events={children} /> : null}
            </article>
          </li>
        );
      })}
    </ol>
  );
}

function ParallelLanes({ events }: { events: PipelineStatusEvent[] }): React.JSX.Element {
  return (
    <div className="parallel-lanes" aria-label="Parallel agents">
      {events.map((event) => (
        <div className="parallel-lane" data-state={event.state} key={event.stage}>
          <span className="lane-state" aria-hidden="true" />
          <span>{event.agent_label}</span>
          <span className="font-tabular">{event.progress === null ? "—" : `${Math.round(event.progress * 100)}%`}</span>
        </div>
      ))}
    </div>
  );
}

function StageStateIcon({ state }: { state: PipelineStatusEvent["state"] }): React.JSX.Element {
  const props = { "aria-hidden": true, size: 18 } as const;
  if (state === "done") return <Check {...props} />;
  if (state === "running") return <Cog {...props} />;
  if (state === "needs_review") return <Pause {...props} />;
  if (state === "error") return <AlertTriangle {...props} />;
  if (state === "queued") return <Circle {...props} />;
  return <RotateCw {...props} />;
}
