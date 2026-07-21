import { ArrowLeft, CheckCircle2, ShieldAlert } from "lucide-react";
import { useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { riversideRecord } from "../../../mock/fixtures";
import { apiClient } from "../../lib/api/client";
import { webConfig } from "../../lib/env";
import { RecordReviewPane } from "./RecordReviewPane";
import { buildReviewFields, requiresReview } from "./review-model";
import { SourceDocumentPane } from "./SourceDocumentPane";
import "./review.css";

export function ReviewPage(): React.JSX.Element {
  const { runId } = useParams();
  const navigate = useNavigate();
  const fields = useMemo(() => buildReviewFields(riversideRecord), []);
  const firstEvidence = fields.find((field) => field.sourceQuote !== null) ?? fields[0]!;
  const [selected, setSelected] = useState(firstEvidence);
  const [page, setPage] = useState(selected.sourcePage ?? 1);
  const [approving, setApproving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const reviewCount = fields.filter((field) => requiresReview(field)).length;

  if (runId === undefined) return <main className="p-8">Run identifier is missing.</main>;
  const activeRunId = runId;
  if (webConfig.apiMode === "real") {
    return (
      <main className="mx-auto max-w-3xl px-5 py-16">
        <div className="rounded-lg border border-review/30 bg-surface p-6">
          <ShieldAlert aria-hidden="true" className="text-review" size={24} />
          <h1 className="mt-4 text-2xl font-semibold">Source review is waiting on its retrieval contract.</h1>
          <p className="mt-3 leading-7 text-ink-green/65">The live API does not yet expose the approved draft together with rendered source pages. Bridgeline will not substitute Riverside mock evidence in real mode.</p>
          <Link className="mt-5 inline-flex items-center gap-2 text-sm font-medium text-deep-moss underline" to={`/runs/${activeRunId}`}><ArrowLeft aria-hidden="true" size={15} /> Return to run</Link>
        </div>
      </main>
    );
  }

  async function approve(): Promise<void> {
    setApproving(true);
    setError(null);
    try {
      await apiClient.approveRun(activeRunId, "PRIYA-CASE-MANAGER");
      navigate(`/runs/${activeRunId}`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Approval could not be recorded.");
      setApproving(false);
    }
  }

  return (
    <main className="mx-auto max-w-[104rem] px-3 py-5 sm:px-5 lg:px-8">
      <header className="mb-5 flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
        <div>
          <Link className="inline-flex items-center gap-2 text-xs font-medium text-ink-green/60" to={`/runs/${activeRunId}`}><ArrowLeft aria-hidden="true" size={14} /> Back to observable run</Link>
          <p className="mt-4 font-mono text-[0.62rem] tracking-[0.12em] text-deep-moss uppercase">Human approval · source-grounded review</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-[-0.025em]">Verify the field. See the evidence.</h1>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <div className="inline-flex items-center gap-2 rounded-lg border border-review/30 bg-sand-peach/25 px-3 py-2 text-sm text-review"><ShieldAlert aria-hidden="true" size={17} /> {reviewCount} fields below threshold</div>
          <button className="inline-flex items-center gap-2 rounded-lg bg-deep-moss px-5 py-3 text-sm font-medium text-paper-cream disabled:opacity-60" disabled={approving} onClick={() => void approve()} type="button"><CheckCircle2 aria-hidden="true" size={17} /> {approving ? "Recording approval…" : "Approve verified record"}</button>
        </div>
      </header>
      {error !== null ? <p className="mb-4 rounded-lg border border-finding/25 bg-surface p-3 text-sm text-finding" role="alert">{error} Try again; the run remains safely paused.</p> : null}
      <div className="review-grid grid items-start gap-4">
        <div className="lg:sticky lg:top-20">
          <SourceDocumentPane field={selected} onPageChange={setPage} page={page} pageCount={riversideRecord.extraction_meta.page_count} />
        </div>
        <RecordReviewPane
          fields={fields}
          onSelect={(field) => { setSelected(field); if (field.sourcePage !== null) setPage(field.sourcePage); }}
          selectedKey={selected.key}
        />
      </div>
    </main>
  );
}
