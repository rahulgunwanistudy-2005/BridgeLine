import { ChevronRight, Pause, Play, RotateCcw, SkipForward, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { TransferSpine, type TransferStage } from "../../components/TransferSpine";
import { RIVERSIDE_DEMO } from "../../lib/riverside";
import "./judge.css";

const DURATION_SECONDS = 30;
const phaseStarts = [0, 3, 6, 10, 14, 17, 21, 24, 27];
const phaseLabels = ["Document", "Ingest", "Extract", "Evidence", "Verify", "Derive", "Citation", "Deliver", "Outcome"];
const transferStageForPhase: TransferStage[] = ["source", "source", "evidence", "evidence", "verify", "cite", "cite", "deliver", "confirm"];

function phaseFor(seconds: number): number {
  return phaseStarts.reduce((active, start, index) => seconds >= start ? index : active, 0);
}

export function JudgeModePage(): React.JSX.Element {
  const navigate = useNavigate();
  const [elapsed, setElapsed] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [started, setStarted] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);
  const lastTick = useRef<number | null>(null);
  const phase = phaseFor(elapsed);

  useEffect(() => {
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = (): void => setReducedMotion(query.matches);
    update();
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);

  useEffect(() => {
    if (!playing || reducedMotion) return;
    const timer = window.setInterval(() => {
      const now = performance.now();
      const delta = lastTick.current === null ? 0 : (now - lastTick.current) / 1000;
      lastTick.current = now;
      setElapsed((current) => {
        const next = Math.min(DURATION_SECONDS, current + delta);
        if (next >= DURATION_SECONDS) setPlaying(false);
        return next;
      });
    }, 80);
    return () => window.clearInterval(timer);
  }, [playing, reducedMotion]);

  function start(): void {
    setStarted(true);
    lastTick.current = performance.now();
    setPlaying(!reducedMotion);
  }

  function replay(): void {
    setElapsed(0);
    setStarted(true);
    lastTick.current = performance.now();
    setPlaying(!reducedMotion);
  }

  function toggle(): void {
    lastTick.current = performance.now();
    setPlaying((value) => !value);
  }

  function nextReducedPhase(): void {
    const next = phaseStarts[phase + 1];
    if (next === undefined) navigate("/dashboard?judge=complete");
    else setElapsed(next);
  }

  return (
    <main className={`judge-mode judge-phase-${phase}`}>
      <header className="judge-topbar">
        <Link to="/" className="judge-brand"><span>§</span> Bridgeline</Link>
        <div className="judge-stage-label"><span>{String(phase + 1).padStart(2, "0")}</span> {phaseLabels[phase]}</div>
        <button aria-label="Exit Judge Mode" className="judge-icon-button" onClick={() => navigate("/dashboard")} type="button"><X size={18} /></button>
      </header>

      <div className="judge-progress" aria-label={`Judge Mode ${Math.round((elapsed / DURATION_SECONDS) * 100)}% complete`} role="progressbar" aria-valuemin={0} aria-valuemax={30} aria-valuenow={Math.round(elapsed)}><span style={{ width: `${(elapsed / DURATION_SECONDS) * 100}%` }} /></div>

      <section className="judge-stage" aria-live="polite">
        <div className="judge-shared-object"><TransferSpine controlledStage={transferStageForPhase[phase] ?? "source"} cinematic /></div>

        {phase === 3 ? (
          <div className="judge-evidence-proof">
            <div className="judge-evidence-page"><img alt="Rendered Riverside IEP page 2" src="/mock/riverside/RIV-1001-page-2.png" /><span aria-hidden="true" /></div>
            <div className="judge-evidence-value"><small>Extracted value · exact source attached</small><strong>Provide 50% extended time on all classroom tests and quizzes.</strong><blockquote>“across all classes” · page 2</blockquote></div>
          </div>
        ) : null}

        <div className="judge-narrative">
          <p>{narratives[phase]?.eyebrow}</p>
          <h1>{narratives[phase]?.title}</h1>
          <span>{narratives[phase]?.detail}</span>
        </div>
      </section>

      <footer className="judge-controls">
        {!started ? <button className="judge-start" onClick={start} type="button"><Play fill="currentColor" size={16} /> Start 30-second walkthrough</button> : (
          <>
            {reducedMotion ? <button className="judge-start" onClick={nextReducedPhase} type="button">Next chapter <ChevronRight size={16} /></button> : <button className="judge-control" onClick={toggle} type="button">{playing ? <><Pause size={15} /> Pause</> : <><Play size={15} /> Resume</>}</button>}
            <button className="judge-control" onClick={replay} type="button"><RotateCcw size={15} /> Replay</button>
          </>
        )}
        <span className="judge-time">{Math.ceil(elapsed)} / 30 sec</span>
        <button className="judge-control" onClick={() => navigate("/dashboard?judge=skipped")} type="button"><SkipForward size={15} /> Skip to product</button>
      </footer>
    </main>
  );
}

const narratives = [
  { eyebrow: "The gap", title: "Finalized is not delivered.", detail: "A legal duty can remain trapped inside a document no classroom teacher has seen." },
  { eyebrow: "Ingest", title: "The source enters intact.", detail: "Bridgeline opens the document, page by page, without changing its legal language." },
  { eyebrow: "Extract", title: "Facts become structured—not untethered.", detail: "Every value keeps its page, exact quote, and confidence." },
  { eyebrow: "Evidence", title: "The claim and its source stay side by side.", detail: "A reviewer sees the scan, the extracted value, and the highlighted evidence together." },
  { eyebrow: "Human approval", title: "AI preparation is not legal truth.", detail: "Priya verifies the record before any classroom responsibility exists." },
  { eyebrow: "Deterministic rules", title: "Approved facts become named duties.", detail: "No model can create, waive, alter, or reword the obligation." },
  { eyebrow: "Legal traceability", title: "Every duty carries its federal anchor.", detail: "The citation is not metadata. It is the visible spine of the workflow." },
  { eyebrow: "Delivery", title: "The obligation reaches a responsible person.", detail: `${RIVERSIDE_DEMO.teacher.name} receives the exact action, source provenance, and classroom guidance.` },
  { eyebrow: "Operational truth", title: "Three confirmed. Three still missing.", detail: "Bridgeline reveals the distance between existing on paper and happening in class." },
] as const;
