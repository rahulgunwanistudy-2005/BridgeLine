import { AlertCircle, Check, Edit3, FileWarning, LocateFixed, X } from "lucide-react";
import { useMemo, useState } from "react";

import type { ReviewField, ReviewGroup } from "./review-model";
import { requiresReview } from "./review-model";

interface RecordReviewPaneProps {
  fields: ReviewField[];
  selectedKey: string;
  onSelect: (field: ReviewField) => void;
}

const groups: ReviewGroup[] = ["Identity and dates", "Accommodations", "Services", "Goals"];

export function RecordReviewPane({ fields, selectedKey, onSelect }: RecordReviewPaneProps): React.JSX.Element {
  const grouped = useMemo(
    () => new Map(groups.map((group) => [group, fields.filter((field) => field.group === group)])),
    [fields],
  );
  return (
    <section className="document-register rounded-[2px] border border-warm-stone bg-paper-cream">
      <div className="border-b border-warm-stone px-5 py-4">
        <p className="font-mono text-[0.62rem] tracking-[0.1em] text-ink-green/55 uppercase">Extracted IEPRecord · draft</p>
        <h2 className="mt-2 font-serif text-2xl font-semibold">Aanya Sharma</h2>
      </div>
      <div className="max-h-[calc(100vh-17rem)] overflow-y-auto">
        {groups.map((group) => (
          <section key={group}>
            <h3 className="sticky top-0 z-10 border-y border-warm-stone bg-paper-cream/95 px-5 py-2 font-mono text-[0.62rem] tracking-[0.1em] text-ink-green/55 uppercase backdrop-blur-sm">
              {group}
            </h3>
            <div>
              {(grouped.get(group) ?? []).map((field) => (
                <ReviewFieldRow field={field} key={field.key} onSelect={onSelect} selected={selectedKey === field.key} />
              ))}
            </div>
          </section>
        ))}
      </div>
    </section>
  );
}

function ReviewFieldRow({ field, selected, onSelect }: { field: ReviewField; selected: boolean; onSelect: (field: ReviewField) => void }): React.JSX.Element {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(field.value ?? "");
  const flagged = requiresReview(field);
  return (
    <article className={`border-b border-warm-stone/70 px-5 py-4 ${selected ? "bg-sand-peach/25" : ""}`}>
      <div className="flex items-start justify-between gap-3">
        <button className="min-w-0 flex-1 text-left" onClick={() => onSelect(field)} type="button">
          <span className="flex items-center gap-2 text-xs font-medium text-ink-green/55">
            {field.label}
            {flagged ? <span className="inline-flex items-center gap-1 text-review"><AlertCircle aria-hidden="true" size={13} /> Review</span> : <Check aria-label="Confidence accepted" className="text-confirmed" size={13} />}
          </span>
          {editing ? (
            <textarea aria-label={`Edit ${field.label}`} className="mt-2 min-h-24 w-full resize-y rounded-[2px] border border-deep-moss bg-surface p-2 font-serif text-sm" onChange={(event) => setValue(event.currentTarget.value)} onClick={(event) => event.stopPropagation()} value={value} />
          ) : (
            <span className="mt-1 block font-serif text-[0.98rem] leading-6">{value.length === 0 ? <em className="text-ink-green/50">Not stated</em> : value}</span>
          )}
        </button>
        <button aria-label={editing ? `Finish editing ${field.label}` : `Edit ${field.label}`} className="grid size-8 shrink-0 place-items-center rounded-[2px] border border-warm-stone" onClick={() => setEditing((current) => !current)} type="button">
          {editing ? <X aria-hidden="true" size={14} /> : <Edit3 aria-hidden="true" size={14} />}
        </button>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2 font-mono text-[0.62rem]">
        <span className={`rounded-[2px] border px-2 py-1 ${flagged ? "border-review/40 text-review" : "border-warm-stone text-ink-green/60"}`}>
          Confidence {field.confidence.toFixed(2)}
        </span>
        {field.sourcePage === null ? (
          <span className="inline-flex items-center gap-1 text-ink-green/45"><FileWarning aria-hidden="true" size={12} /> No source anchor in contract</span>
        ) : (
          <button className="inline-flex items-center gap-1 text-deep-moss underline decoration-warm-stone underline-offset-4" onClick={() => onSelect(field)} type="button"><LocateFixed aria-hidden="true" size={12} /> Page {field.sourcePage}</button>
        )}
      </div>
      {field.reconciliationStatus === "ambiguous" ? (
        <p className="mt-3 border-l-2 border-review pl-3 text-xs leading-5 text-review">This item may match a prior IEP version. Confirm its identity before approval.</p>
      ) : null}
      {field.scopeReferences.length > 0 ? (
        <div className="mt-3 grid gap-2">
          {field.scopeReferences.map((scope, index) => (
            <div className={`grid grid-cols-[auto_1fr_auto] items-start gap-2 border-l-2 px-3 py-2 text-xs ${scope.confidence < 0.9 ? "border-review bg-sand-peach/20" : "border-deep-moss/25"}`} key={`${scope.scope}-${scope.ref}-${index}`}>
              <span className="font-mono text-[0.58rem] tracking-wide text-ink-green/50 uppercase">{scope.scope}</span>
              <span className="font-serif">“{scope.ref}”</span>
              <span className="font-tabular text-[0.62rem]">{scope.confidence.toFixed(2)}</span>
            </div>
          ))}
        </div>
      ) : null}
    </article>
  );
}
