import { AlertOctagon, ArrowDown, CalendarClock, CheckCircle2, Circle, Clock3, Minus, RefreshCw, UsersRound } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { CitationChip } from "../../components/CitationChip";
import { apiClient } from "../../lib/api/client";
import type { Deadline, Finding, FindingStatus, RegistryResponse } from "../../lib/api/contracts";
import { cornellCitationUrl } from "../../lib/citations";
import { groupFindings, orderedDeadlines, studentName } from "./dashboard-model";
import "./dashboard.css";

type FeedFilter = "all" | FindingStatus;

export function DashboardPage(): React.JSX.Element {
  const [findings, setFindings] = useState<Finding[] | null>(null);
  const [deadlines, setDeadlines] = useState<Deadline[] | null>(null);
  const [registry, setRegistry] = useState<RegistryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<FeedFilter>("all");

  useEffect(() => {
    let active = true;
    Promise.all([apiClient.findings(), apiClient.deadlines(), apiClient.rules()])
      .then(([nextFindings, nextDeadlines, nextRegistry]) => {
        if (!active) return;
        setFindings(nextFindings);
        setDeadlines(nextDeadlines);
        setRegistry(nextRegistry);
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : "Compliance data could not be loaded.");
      });
    return () => { active = false; };
  }, []);

  const sections = useMemo(() => groupFindings(findings ?? []), [findings]);
  const visibleFeed = (findings ?? []).filter((finding) => filter === "all" || finding.status === filter);

  async function transition(finding: Finding): Promise<void> {
    const nextStatus: FindingStatus = finding.status === "open" ? "resolved" : "open";
    try {
      const updated = await apiClient.transitionFinding(finding.id, nextStatus);
      setFindings((current) => current?.map((item) => (item.id === updated.id ? updated : item)) ?? null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The finding could not be updated.");
    }
  }

  function description(ruleId: string): string {
    return registry?.rules.find((rule) => rule.id === ruleId)?.description ?? "Open the cited regulation and registry description.";
  }

  if (error !== null && findings === null) {
    return <main className="mx-auto max-w-3xl px-5 py-16"><div className="rounded-lg border border-finding/30 bg-surface p-6"><AlertOctagon className="text-finding" size={24} /><h1 className="mt-4 text-2xl font-semibold">Compliance data did not load.</h1><p className="mt-2 text-ink-green/65">{error}</p><button className="mt-5 inline-flex items-center gap-2 rounded-lg bg-deep-moss px-4 py-2 text-sm text-paper-cream" onClick={() => window.location.reload()} type="button"><RefreshCw size={15} /> Retry dashboard</button></div></main>;
  }

  return (
    <main className="mx-auto max-w-[96rem] px-4 py-8 sm:px-6 lg:px-8 lg:py-12">
      <header className="dashboard-header flex flex-col justify-between gap-5">
        <div><p className="font-mono text-xs tracking-[0.12em] text-deep-moss uppercase">Riverside compliance · 13 Nov 2026</p><h1 className="mt-3 text-4xl font-semibold tracking-[-0.03em]">What exists on paper. What reached the classroom.</h1><p className="mt-3 max-w-2xl text-sm leading-6 text-ink-green/65">Derived from approved IEP versions, instructional calendars, service logs, and teacher confirmations.</p></div>
        <div className="grid grid-cols-3 gap-2 text-center">
          <Metric value="3" label="Open findings" tone="finding" />
          <Metric value="2" label="Overdue dates" tone="review" />
          <Metric value="9" label="Students clear" tone="confirmed" />
        </div>
      </header>

      {findings === null || deadlines === null ? <DashboardSkeleton /> : (
        <div className="dashboard-grid mt-8 grid gap-5">
          <div className="grid gap-5">
            <section aria-labelledby="implementation-gaps" className="rounded-lg border border-deep-moss/15 bg-surface shadow-sm">
              <SectionHeading eyebrow="First action" icon={<UsersRound aria-hidden="true" size={18} />} id="implementation-gaps" title="Implementation gaps" />
              {sections.implementationGaps.map((finding) => <GapFinding description={description(finding.rule_id)} finding={finding} key={finding.id} />)}
              <div className="flex items-center gap-3 border-t border-deep-moss/10 px-5 py-4 text-sm text-confirmed"><CheckCircle2 aria-hidden="true" size={17} /> Nine other Riverside students have no active implementation gap.</div>
            </section>

            <section aria-labelledby="service-minutes" className="rounded-lg border border-deep-moss/15 bg-surface shadow-sm">
              <SectionHeading eyebrow="Weekly accounting" icon={<Clock3 aria-hidden="true" size={18} />} id="service-minutes" title="Service-minute variance" />
              {sections.serviceVariances.map((finding) => <ServiceVariance description={description(finding.rule_id)} finding={finding} key={finding.id} />)}
            </section>

            <section aria-labelledby="findings-feed" className="rounded-lg border border-deep-moss/15 bg-surface shadow-sm">
              <div className="flex flex-col justify-between gap-3 border-b border-deep-moss/10 px-5 py-4 sm:flex-row sm:items-center">
                <div><p className="font-mono text-[0.6rem] tracking-[0.1em] text-ink-green/45 uppercase">Audited lifecycle</p><h2 className="mt-1 text-xl font-semibold" id="findings-feed">Findings feed</h2></div>
                <div className="flex rounded-lg border border-deep-moss/15 p-1" aria-label="Filter findings">
                  {(["all", "open", "resolved"] as const).map((value) => <button aria-pressed={filter === value} className={`rounded-md px-3 py-1.5 text-xs font-medium ${filter === value ? "bg-deep-moss text-paper-cream" : "text-ink-green/60"}`} key={value} onClick={() => setFilter(value)} type="button">{value[0]?.toUpperCase()}{value.slice(1)}</button>)}
                </div>
              </div>
              {visibleFeed.length === 0 ? <div className="p-8 text-center"><CheckCircle2 className="mx-auto text-confirmed" size={24} /><p className="mt-3 font-medium">Nothing is waiting in this view.</p><p className="mt-1 text-sm text-ink-green/55">Change the filter to inspect another lifecycle state.</p></div> : visibleFeed.map((finding) => <FeedRow description={description(finding.rule_id)} finding={finding} key={finding.id} onTransition={() => void transition(finding)} />)}
            </section>
          </div>

          <aside className="grid content-start gap-5">
            <section aria-labelledby="deadline-calendar" className="rounded-lg border border-deep-moss/15 bg-surface shadow-sm">
              <SectionHeading eyebrow="School-local dates" icon={<CalendarClock aria-hidden="true" size={18} />} id="deadline-calendar" title="Deadline calendar" />
              <div>{orderedDeadlines(deadlines).map((deadline) => <DeadlineRow deadline={deadline} description={description(deadline.rule_id)} key={deadline.id} />)}</div>
            </section>
            <section className="rounded-lg bg-deep-moss p-5 text-paper-cream">
              <p className="font-mono text-[0.6rem] tracking-[0.12em] text-paper-cream/55 uppercase">Coverage</p>
              <p className="mt-3 text-3xl font-semibold">12 / 12</p>
              <p className="mt-2 text-sm leading-6 text-paper-cream/75">Roster students have a current approved IEP version in effect.</p>
            </section>
          </aside>
        </div>
      )}
      {error !== null ? <p className="mt-5 rounded-lg border border-finding/25 bg-surface p-3 text-sm text-finding" role="alert">{error}</p> : null}
    </main>
  );
}

function Metric({ value, label, tone }: { value: string; label: string; tone: "finding" | "review" | "confirmed" }): React.JSX.Element {
  const toneClass = tone === "finding" ? "text-finding" : tone === "review" ? "text-review" : "text-confirmed";
  return <div className="min-w-24 rounded-lg border border-deep-moss/15 bg-surface px-3 py-3"><p className={`font-tabular text-xl font-medium ${toneClass}`}>{value}</p><p className="mt-1 text-[0.65rem] text-ink-green/50">{label}</p></div>;
}

function SectionHeading({ eyebrow, icon, id, title }: { eyebrow: string; icon: React.ReactNode; id: string; title: string }): React.JSX.Element {
  return <div className="flex items-center gap-3 border-b border-deep-moss/10 px-5 py-4"><span className="grid size-9 place-items-center rounded-lg bg-cool-mineral text-deep-moss">{icon}</span><div><p className="font-mono text-[0.6rem] tracking-[0.1em] text-ink-green/45 uppercase">{eyebrow}</p><h2 className="mt-1 text-xl font-semibold" id={id}>{title}</h2></div></div>;
}

function GapFinding({ finding, description }: { finding: Finding; description: string }): React.JSX.Element {
  const confirmed = finding.related_refs.confirmed_classes as string[] | undefined;
  const unconfirmed = finding.related_refs.unconfirmed_classes as string[] | undefined;
  return <article className="p-5"><div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-start"><div><p className="text-xs font-medium text-ink-green/50">{studentName(finding.student_ref)} · Extended time</p><h3 className="mt-2 max-w-3xl text-2xl font-semibold leading-tight">Extended time — confirmed in <span className="font-tabular">3 of 6</span> classes</h3><p className="mt-3 max-w-2xl text-sm leading-6 text-ink-green/65">A legally mandated accommodation reached English, Mathematics, and Biology. Three classrooms have not confirmed it.</p></div><CitationChip citation={finding.citation} description={description} href={cornellCitationUrl(finding.citation)} /></div><div className="mt-5 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">{(confirmed ?? []).map((classRef) => <ClassState classRef={classRef} confirmed key={classRef} />)}{(unconfirmed ?? []).map((classRef) => <ClassState classRef={classRef} confirmed={false} key={classRef} />)}</div></article>;
}

function ClassState({ classRef, confirmed }: { classRef: string; confirmed: boolean }): React.JSX.Element {
  return <div className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-xs ${confirmed ? "border-confirmed/20 bg-confirmed/5 text-confirmed" : "border-warm-stone bg-paper-cream text-ink-green/60"}`}>{confirmed ? <CheckCircle2 aria-hidden="true" size={14} /> : <Circle aria-hidden="true" size={14} />}<span className="font-tabular">{classRef}</span></div>;
}

function ServiceVariance({ finding, description }: { finding: Finding; description: string }): React.JSX.Element {
  const required = Number(finding.measurements.required_minutes ?? 0); const delivered = Number(finding.measurements.delivered_minutes ?? 0); const percent = Math.round((delivered / required) * 100);
  return <article className="grid gap-5 p-5 lg:grid-cols-[1fr_auto] lg:items-center"><div><p className="text-xs text-ink-green/50">{studentName(finding.student_ref)} · Specialized academic instruction</p><div className="mt-2 flex items-baseline gap-3"><span className="font-tabular text-3xl font-medium">{delivered}</span><span className="text-sm text-ink-green/55">of {required} min/week</span><span className="inline-flex items-center gap-1 font-tabular text-sm text-finding"><ArrowDown aria-hidden="true" size={14} /> −20</span></div><div className="mt-4 h-2 overflow-hidden rounded-full bg-cool-mineral"><div className="h-full rounded-full bg-finding" style={{ width: `${percent}%` }} /></div></div><CitationChip citation={finding.citation} description={description} href={cornellCitationUrl(finding.citation)} /></article>;
}

function DeadlineRow({ deadline, description }: { deadline: Deadline; description: string }): React.JSX.Element {
  const overdue = deadline.status === "overdue";
  return <article className="border-b border-deep-moss/10 p-5 last:border-0"><div className="flex items-start justify-between gap-3"><div><div className="flex items-center gap-2"><span className={`size-2 ${overdue ? "rotate-45 bg-finding" : "rounded-full bg-review"}`} aria-hidden="true" /><p className="text-xs font-medium text-ink-green/50">{studentName(deadline.student_ref)}</p></div><h3 className="mt-2 font-medium">{deadline.description}</h3></div><span className={`rounded-[2px] border px-2 py-1 font-mono text-[0.6rem] uppercase ${overdue ? "rotate-[-2deg] border-finding text-finding" : "border-review/40 text-review"}`}>{overdue ? "Overdue" : "Upcoming"}</span></div><div className="mt-3 flex items-end justify-between gap-3"><div><p className="font-tabular text-lg">{formatDate(deadline.legal_due_on)}</p><p className="mt-1 text-xs text-ink-green/45">Legal date · action {formatDate(deadline.action_due_on)}</p></div><CitationChip citation={deadline.citation} description={description} href={cornellCitationUrl(deadline.citation)} /></div></article>;
}

function FeedRow({ finding, description, onTransition }: { finding: Finding; description: string; onTransition: () => void }): React.JSX.Element {
  const resolved = finding.status === "resolved";
  return <article className={`grid gap-4 border-b border-deep-moss/10 p-5 last:border-0 lg:grid-cols-[1fr_auto] lg:items-center ${resolved ? "opacity-60" : ""}`}><div className="flex gap-3"><span className={`mt-1 grid size-7 shrink-0 place-items-center rounded-full ${resolved ? "bg-confirmed/10 text-confirmed" : "bg-review/10 text-review"}`}>{resolved ? <CheckCircle2 aria-hidden="true" size={15} /> : <Minus aria-hidden="true" size={15} />}</span><div><p className="text-xs text-ink-green/45">{studentName(finding.student_ref)} · {finding.status}</p><h3 className="mt-1 font-medium">{finding.title}</h3><p className="mt-1 max-w-2xl text-sm leading-6 text-ink-green/60">{finding.detail}</p><div className="mt-3"><CitationChip citation={finding.citation} description={description} href={cornellCitationUrl(finding.citation)} /></div></div></div><button className="rounded-lg border border-deep-moss/20 px-3 py-2 text-xs font-medium" onClick={onTransition} type="button">{resolved ? "Reopen finding" : "Resolve finding"}</button></article>;
}

function DashboardSkeleton(): React.JSX.Element { return <div className="dashboard-grid mt-8 grid gap-5" aria-label="Loading compliance dashboard"><div className="grid gap-5">{[1,2,3].map((item) => <div className="h-48 animate-pulse rounded-lg bg-surface" key={item} />)}</div><div className="h-96 animate-pulse rounded-lg bg-surface" /></div>; }

function formatDate(value: string): string { return new Intl.DateTimeFormat("en-US", { day: "2-digit", month: "short", year: "numeric", timeZone: "UTC" }).format(new Date(`${value}T12:00:00Z`)); }
