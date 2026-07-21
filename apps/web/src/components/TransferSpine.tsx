import { Check, Circle, LockKeyhole, ScanLine } from "lucide-react";
import { useEffect, useRef, useState, type CSSProperties, type PointerEvent } from "react";
import "./transfer-spine.css";

export const transferStages = ["source", "evidence", "verify", "cite", "deliver", "confirm"] as const;
export type TransferStage = (typeof transferStages)[number];

interface TransferSpineProps {
  controlledStage?: TransferStage;
  cinematic?: boolean;
}

const stageCopy: Record<TransferStage, { label: string; detail: string }> = {
  source: { label: "Source", detail: "Page 2 · exact approved language" },
  evidence: { label: "Evidence", detail: "The passage stays tethered to its origin" },
  verify: { label: "Verify", detail: "A human aligns facts before duties exist" },
  cite: { label: "Cite", detail: "34 CFR §300.323(d)(2)(ii)" },
  deliver: { label: "Deliver", detail: "Six responsible classrooms" },
  confirm: { label: "Confirm", detail: "3 of 6 confirmed · 3 still open" },
};

const classrooms = ["English", "Mathematics", "Biology", "History", "PE", "Art"];

export function initialTransferStage(reducedMotion: boolean): TransferStage {
  return reducedMotion ? "confirm" : "source";
}

export function TransferSpine({ controlledStage, cinematic = false }: TransferSpineProps): React.JSX.Element {
  const [localStage, setLocalStage] = useState<TransferStage>(() => initialTransferStage(window.matchMedia("(prefers-reduced-motion: reduce)").matches));
  const [reducedMotion, setReducedMotion] = useState(() => window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  const sceneRef = useRef<HTMLElement | null>(null);
  const stage = controlledStage ?? localStage;
  const stageIndex = transferStages.indexOf(stage);

  useEffect(() => {
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = (): void => setReducedMotion(query.matches);
    update();
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);

  useEffect(() => {
    if (controlledStage !== undefined || reducedMotion) {
      if (controlledStage === undefined && reducedMotion) setLocalStage("confirm");
      return;
    }
    const timers = transferStages.slice(1).map((next, index) => window.setTimeout(() => setLocalStage(next), 500 + index * 420));
    return () => timers.forEach((timer) => window.clearTimeout(timer));
  }, [controlledStage, reducedMotion]);

  useEffect(() => {
    const updateScroll = (): void => {
      const progress = Math.min(1, window.scrollY / 520);
      sceneRef.current?.style.setProperty("--spine-scroll", String(progress));
    };
    updateScroll();
    window.addEventListener("scroll", updateScroll, { passive: true });
    return () => window.removeEventListener("scroll", updateScroll);
  }, []);

  function move(event: PointerEvent<HTMLElement>): void {
    if (event.pointerType === "touch" || reducedMotion) return;
    const bounds = event.currentTarget.getBoundingClientRect();
    const x = ((event.clientX - bounds.left) / bounds.width - 0.5) * 2;
    const y = ((event.clientY - bounds.top) / bounds.height - 0.5) * 2;
    event.currentTarget.style.setProperty("--spine-x", `${(x * 5).toFixed(2)}deg`);
    event.currentTarget.style.setProperty("--spine-y", `${(y * -3).toFixed(2)}deg`);
  }

  function resetPointer(event: PointerEvent<HTMLElement>): void {
    event.currentTarget.style.setProperty("--spine-x", "0deg");
    event.currentTarget.style.setProperty("--spine-y", "0deg");
  }

  const style = { "--stage": stageIndex } as CSSProperties;

  return (
    <figure
      className={`transfer-sculpture transfer-sculpture--${stage} ${cinematic ? "transfer-sculpture--cinematic" : ""}`}
      onPointerMove={move}
      onPointerLeave={resetPointer}
      ref={sceneRef}
      style={style}
    >
      <figcaption className="sr-only">A source-grounded IEP accommodation passes through human verification and a federal citation into six classroom responsibilities, three confirmed and three awaiting confirmation.</figcaption>

      <div className="transfer-object" aria-hidden="true">
        <div className="case-file-shell"><span>IEP</span><small>FINAL · 2026</small></div>
        <div className="source-sheet">
          <div className="source-sheet-head"><span>Individualized education program</span><span>02 / 04</span></div>
          <div className="source-lines"><i /><i /><i /></div>
          <p>Provide 50% extended time on all classroom tests and quizzes.</p>
          <div className="source-scope">across all classes</div>
          <div className="source-field-grid"><i /><i /><i /><i /></div>
        </div>

        <div className="evidence-slip">
          <span>Exact source · p2</span>
          <strong>50% extended time</strong>
          <small>“across all classes”</small>
        </div>
        <div className="evidence-tether"><i /><i /><i /></div>

        <div className="verification-gate">
          <div className="gate-rail gate-rail--top" />
          <div className="gate-lock"><LockKeyhole size={14} /><span>Priya</span></div>
          <div className="gate-rail gate-rail--bottom" />
          <div className="registration-marks"><i /><i /><i /><i /></div>
        </div>

        <div className="citation-spine">
          <span className="citation-spine-symbol">§</span>
          <span className="citation-spine-title">34 CFR</span>
          <strong>300.323</strong>
          <span className="citation-spine-path">(d) · (2) · (ii)</span>
          <small>Verified responsibility</small>
        </div>

        <div className="responsibility-rack">
          <div className="rack-action">Provide 50% extended time</div>
          {classrooms.map((classroom, index) => (
            <div className={`responsibility-tab ${index < 3 ? "is-confirmed" : ""}`} key={classroom} style={{ "--tab-offset": `${index * 0.55}rem` } as CSSProperties}>
              <span>{String(index + 1).padStart(2, "0")}</span>
              <strong>{classroom}</strong>
              {index < 3 ? <Check size={13} /> : <Circle size={13} />}
            </div>
          ))}
          <div className="rack-bracket" />
        </div>
      </div>

      <div className="transfer-readout" aria-live="polite">
        <span><ScanLine size={14} /> {stageCopy[stage].label}</span>
        <strong>{stageCopy[stage].detail}</strong>
        <div className="transfer-meter">{transferStages.map((item, index) => <i className={index <= stageIndex ? "is-active" : ""} key={item} />)}</div>
      </div>

      {!cinematic ? (
        <div className="transfer-stage-nav" aria-label="Explore obligation transfer stages">
          {transferStages.map((item, index) => (
            <button aria-pressed={item === stage} onClick={() => setLocalStage(item)} type="button" key={item}>
              <span>{String(index + 1).padStart(2, "0")}</span>{stageCopy[item].label}
            </button>
          ))}
        </div>
      ) : null}
    </figure>
  );
}
