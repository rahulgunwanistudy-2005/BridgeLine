import { ChevronRight, Pause, Play, RotateCcw, SkipForward, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { TransferSpine, type TransferStage } from "../../components/TransferSpine";
import "./judge.css";

const DURATION_SECONDS = 30;
const phaseStarts = [0, 4, 9, 14, 18, 23, 27];
const transferStageForPhase: TransferStage[] = ["source", "evidence", "evidence", "verify", "cite", "deliver", "confirm"];

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

  useEffect(() => {
    if (elapsed >= DURATION_SECONDS) navigate("/dashboard?judge=complete");
  }, [elapsed, navigate]);

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
        <div className="judge-stage-label">Following one verified obligation</div>
        <button aria-label="Exit Judge Mode" className="judge-icon-button" onClick={() => navigate("/dashboard")} type="button"><X size={18} /></button>
      </header>

      <section className="judge-stage" aria-live="polite">
        <div className="judge-shared-object"><TransferSpine controlledStage={transferStageForPhase[phase] ?? "source"} cinematic /></div>

        {phase === 2 || phase === 3 ? (
          <div className="judge-evidence-proof">
            <div className="judge-evidence-page"><img alt="Rendered Riverside IEP page 2" src="/mock/riverside/RIV-1001-page-2.png" /><span aria-hidden="true" /></div>
            <div className={`judge-evidence-value ${phase === 3 ? "is-approved" : ""}`}><small>{phase === 3 ? "Human verified · source locked" : "Extracted value · exact source attached"}</small><strong>Provide 50% extended time on all classroom tests and quizzes.</strong><blockquote>“across all classes” · page 2</blockquote><div className="judge-registration" aria-hidden="true"><i /><i /><i /><i /></div></div>
          </div>
        ) : null}

        {phase === 4 ? <div className="judge-citation-frame"><span>One verified duty</span><strong>34 CFR §300.323(d)(2)(ii)</strong><small>Teacher-informed accommodations</small></div> : null}

        <div className="judge-narrative">
          <h1>{narratives[phase]?.title}</h1>
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
  { title: "Finalized. But not delivered." },
  { title: "One duty, still anchored to its source." },
  { title: "The evidence follows the claim." },
  { title: "Human verified." },
  { title: "Federal traceability, intact." },
  { title: `One duty reaches six classrooms.` },
  { title: "3 of 6 confirmed." },
] as const;
