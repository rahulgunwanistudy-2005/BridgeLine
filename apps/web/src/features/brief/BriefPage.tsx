import { AlertTriangle, Check, FileText, Flag, Printer } from "lucide-react";
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { CitationChip } from "../../components/CitationChip";
import { apiClient } from "../../lib/api/client";
import { cornellCitationUrl } from "../../lib/citations";
import { webConfig } from "../../lib/env";
import type { TeacherBrief } from "../../lib/types/generated";
import { RIVERSIDE_DEMO } from "../../lib/riverside";
import "./brief.css";

const DEMO_TEACHER_ID = "T-DELGADO";

export function BriefPage(): React.JSX.Element {
  const { teacherId = DEMO_TEACHER_ID } = useParams();
  const [brief, setBrief] = useState<TeacherBrief | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showFlagForm, setShowFlagForm] = useState(false);
  const [flagReason, setFlagReason] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (webConfig.apiMode === "real") {
      setLoading(false);
      return;
    }
    apiClient
      .teacherBriefs(teacherId)
      .then((briefs) => setBrief(briefs[0] ?? null))
      .catch((cause: unknown) => setError(cause instanceof Error ? cause.message : "Could not load brief."))
      .finally(() => setLoading(false));
  }, [teacherId]);

  async function confirm(): Promise<void> {
    if (brief === null) return;
    setSaving(true);
    setError(null);
    try {
      setBrief(await apiClient.confirmBrief(brief.brief_id));
      setShowFlagForm(false);
    } catch (cause: unknown) {
      setError(cause instanceof Error ? cause.message : "Could not confirm brief.");
    } finally {
      setSaving(false);
    }
  }

  async function flag(): Promise<void> {
    if (brief === null || flagReason.trim() === "") return;
    setSaving(true);
    setError(null);
    try {
      setBrief(await apiClient.flagBrief(brief.brief_id, flagReason.trim()));
      setShowFlagForm(false);
      setFlagReason("");
    } catch (cause: unknown) {
      setError(cause instanceof Error ? cause.message : "Could not flag brief.");
    } finally {
      setSaving(false);
    }
  }

  if (webConfig.apiMode === "real") {
    return (
      <main className="mx-auto max-w-4xl px-5 py-16">
        <EmptyState title="Teacher briefs are not exposed by the current API contract." detail="Switch VITE_API_MODE to mock for the schema-valid Riverside walkthrough. No brief content is fabricated in real mode." />
      </main>
    );
  }

  if (loading) {
    return <main className="mx-auto max-w-4xl px-5 py-16" aria-live="polite">Preparing the authorized class brief…</main>;
  }

  if (brief === null) {
    return (
      <main className="mx-auto max-w-4xl px-5 py-16">
        <EmptyState title="No released brief for this teacher." detail={error ?? "A case manager must release an approved brief before it appears here."} />
      </main>
    );
  }

  const obligationCount = brief.students.reduce((total, student) => total + student.obligations.length, 0);

  return (
    <main className="brief-shell">
      <div className="brief-toolbar brief-actions">
        <div>
          <p className="brief-kicker">Authorized classroom brief</p>
          <p className="text-sm text-ink-green/60">Only the implementation information needed for this class.</p>
        </div>
        <button className="brief-secondary-button" onClick={() => window.print()} type="button">
          <Printer aria-hidden="true" size={16} /> Print brief
        </button>
      </div>

      <article className="brief-paper" aria-labelledby="brief-title">
        <header className="brief-header">
          <div>
            <div className="brief-wordmark"><FileText aria-hidden="true" size={17} /> Bridgeline / teacher copy</div>
            <h1 id="brief-title">English implementation brief</h1>
            <p>{RIVERSIDE_DEMO.teacher.name} · {RIVERSIDE_DEMO.classroom.name} · Period {RIVERSIDE_DEMO.classroom.period} · {brief.class_ref}</p>
          </div>
          <dl className="brief-meta">
            <div><dt>School year</dt><dd>{brief.school_year}</dd></div>
            <div><dt>Students</dt><dd>{brief.students.length}</dd></div>
            <div><dt>Actions</dt><dd>{obligationCount}</dd></div>
            <div><dt>Status</dt><dd className={`brief-status brief-status--${brief.status}`}>{brief.status}</dd></div>
          </dl>
        </header>

        <section className="brief-responsibility" aria-label="Legal responsibility">
          <div>
            <p className="brief-kicker">Your responsibility</p>
            <p className="font-serif text-lg leading-7">{brief.responsibility.text}</p>
          </div>
          <CitationChip citation={brief.responsibility.citation} description="Teachers must be informed of the specific accommodations, modifications, and supports they must provide." href={cornellCitationUrl(brief.responsibility.citation)} />
        </section>

        {brief.students.map((student) => (
          <section className="brief-student" key={student.student_ref}>
            <div className="brief-student-heading">
              <div><p className="brief-kicker">Student</p><h2>{student.student_name}</h2></div>
              <span>{student.student_ref}</span>
            </div>
            <ol className="brief-obligations">
              {student.obligations.map((obligation, index) => (
                <li className="brief-obligation" key={obligation.obligation_id}>
                  <span className="brief-obligation-number">{String(index + 1).padStart(2, "0")}</span>
                  <div>
                    <p className="brief-exact-text">{obligation.accommodation_text}</p>
                    <p className="brief-practice"><strong>In this class</strong> {obligation.practice_text}</p>
                    <div className="brief-provenance">
                      <span>Scope: “across all classes”</span>
                      <span>IEP page {obligation.source_page}</span>
                      <span>{Math.round(obligation.source_confidence * 100)}% source confidence</span>
                    </div>
                  </div>
                  <CitationChip citation={obligation.citation} description="This mandatory action was derived from the approved IEP by the deterministic rules registry." href={cornellCitationUrl(obligation.citation)} />
                </li>
              ))}
            </ol>
          </section>
        ))}

        <footer className="brief-footer">
          <p>Generated {new Date(brief.generated_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric", timeZone: "UTC" })} · Registry {brief.rules_version}</p>
          <p>Accommodation language is copied unchanged from the approved IEP.</p>
        </footer>
      </article>

      <section className="brief-confirmation brief-actions" aria-label="Brief confirmation">
        <div>
          <p className="font-semibold">Can you implement these responsibilities?</p>
          <p className="mt-1 text-sm text-ink-green/65">Confirmation is recorded; flagging requires a reason for case-manager follow-up.</p>
          {brief.status === "confirmed" ? <p className="mt-3 inline-flex items-center gap-2 text-sm font-semibold text-confirmed"><Check size={16} /> Confirmed Nov 13</p> : null}
          {brief.status === "flagged" ? <p className="mt-3 inline-flex items-center gap-2 text-sm font-semibold text-finding"><AlertTriangle size={16} /> Flagged: {brief.flag_reason}</p> : null}
        </div>
        <div className="brief-confirmation-controls">
          <button className="brief-primary-button" disabled={saving || brief.status === "confirmed"} onClick={() => void confirm()} type="button"><Check size={16} /> Confirm responsibilities</button>
          <button className="brief-secondary-button" disabled={saving} onClick={() => setShowFlagForm((shown) => !shown)} type="button"><Flag size={16} /> Flag a barrier</button>
        </div>
        {showFlagForm ? (
          <div className="brief-flag-form">
            <label htmlFor="flag-reason">What is preventing implementation?</label>
            <textarea id="flag-reason" onChange={(event) => setFlagReason(event.target.value)} placeholder="Describe the barrier so the case manager can act." rows={3} value={flagReason} />
            <button className="brief-primary-button" disabled={saving || flagReason.trim() === ""} onClick={() => void flag()} type="button">Send to case manager</button>
          </div>
        ) : null}
        {error !== null ? <p className="brief-error" role="alert">{error}</p> : null}
      </section>
    </main>
  );
}

function EmptyState({ title, detail }: { title: string; detail: string }): React.JSX.Element {
  return <section className="rounded-lg border border-warm-stone bg-paper-cream p-8"><h1 className="text-2xl font-semibold">{title}</h1><p className="mt-3 max-w-2xl text-ink-green/65">{detail}</p></section>;
}
