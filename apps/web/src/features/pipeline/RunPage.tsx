import { ArrowRight, CircleCheck, PauseCircle, Radio, RefreshCw, WifiOff } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { PipelineFlow } from "./PipelineFlow";
import { buildPipelineViewModel } from "./pipeline-model";
import { usePipelineStream } from "./usePipelineStream";

export function RunPage(): React.JSX.Element {
  const { runId } = useParams();
  if (runId === undefined) {
    return <main className="p-8">Run identifier is missing.</main>;
  }
  return <RunContent runId={runId} />;
}

function RunContent({ runId }: { runId: string }): React.JSX.Element {
  const { events, connectionState, error, reconnect } = usePipelineStream(runId);
  const model = buildPipelineViewModel(events);
  const paused = connectionState === "paused";
  const complete = connectionState === "complete";

  return (
    <main className="mx-auto max-w-[96rem] px-4 py-8 sm:px-6 lg:px-8 lg:py-12">
      <div className="mb-8 flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
        <div>
          <p className="font-mono text-xs tracking-[0.12em] text-deep-moss uppercase">Observable run</p>
          <h1 className="mt-3 text-3xl font-semibold tracking-[-0.025em] sm:text-4xl">
            The document is moving toward the classroom.
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-ink-green/65">
            Every line below comes from the durable pipeline event stream. Refreshing or opening
            this run in another tab resumes from its own sequence cursor.
          </p>
        </div>
        <ConnectionStatus state={connectionState} />
      </div>

      {error !== null ? (
        <div className="mb-6 flex items-center justify-between gap-4 rounded-lg border border-finding/25 bg-surface p-4" role="alert">
          <div className="flex items-center gap-3">
            <WifiOff aria-hidden="true" className="text-finding" size={20} />
            <div><p className="font-medium">The live view disconnected.</p><p className="text-sm text-ink-green/60">{error}</p></div>
          </div>
          <button className="inline-flex items-center gap-2 rounded-lg border border-deep-moss/25 px-3 py-2 text-sm font-medium" onClick={reconnect} type="button">
            <RefreshCw aria-hidden="true" size={15} /> Reconnect
          </button>
        </div>
      ) : null}

      <PipelineFlow events={events} />

      {events.length === 0 ? (
        <div className="mt-5 grid gap-2" aria-label="Loading pipeline events">
          <div className="h-3 w-2/3 animate-pulse rounded bg-warm-stone/35" />
          <div className="h-3 w-1/2 animate-pulse rounded bg-warm-stone/25" />
        </div>
      ) : null}

      {model.latest !== null ? (
        <section className="mt-6 grid gap-5 rounded-lg border border-deep-moss/15 bg-surface p-5 shadow-sm md:grid-cols-[1fr_auto] md:items-center">
          <div>
            <p className="font-mono text-[0.65rem] tracking-[0.1em] text-ink-green/50 uppercase">
              Event {String(model.latest.seq).padStart(2, "0")} · {model.latest.agent_label}
            </p>
            <p className="mt-2 max-w-3xl text-sm leading-6">{model.latest.detail}</p>
          </div>
          {paused ? (
            <Link className="inline-flex items-center justify-center gap-2 rounded-lg bg-review px-5 py-3 text-sm font-medium text-surface" to={`/runs/${runId}/review`}>
              Review 2 fields <ArrowRight aria-hidden="true" size={16} />
            </Link>
          ) : complete ? (
            <Link className="inline-flex items-center justify-center gap-2 rounded-lg bg-deep-moss px-5 py-3 text-sm font-medium text-paper-cream" to="/dashboard">
              Open compliance dashboard <ArrowRight aria-hidden="true" size={16} />
            </Link>
          ) : null}
        </section>
      ) : null}
    </main>
  );
}

function ConnectionStatus({ state }: { state: ReturnType<typeof usePipelineStream>["connectionState"] }): React.JSX.Element {
  const complete = state === "complete";
  const paused = state === "paused";
  const Icon = complete ? CircleCheck : paused ? PauseCircle : Radio;
  const copy = complete ? "Run complete" : paused ? "Intentionally paused" : state === "error" ? "Disconnected" : state === "reconnecting" ? "Reconnecting" : "Live event stream";
  return (
    <div className={`inline-flex w-fit items-center gap-2 rounded-full border px-3 py-2 text-xs font-medium ${complete ? "border-confirmed/25 text-confirmed" : paused ? "border-review/30 text-review" : "border-deep-moss/20 text-deep-moss"}`}>
      <Icon aria-hidden="true" size={15} /> {copy}
    </div>
  );
}
