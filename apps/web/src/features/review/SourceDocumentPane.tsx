import { ChevronLeft, ChevronRight, FileSearch } from "lucide-react";

import type { ReviewField } from "./review-model";

interface SourceDocumentPaneProps {
  field: ReviewField;
  page: number;
  pageCount: number;
  onPageChange: (page: number) => void;
}

export function SourceDocumentPane({
  field,
  page,
  pageCount,
  onPageChange,
}: SourceDocumentPaneProps): React.JSX.Element {
  const highlight = highlightPosition(field, page);
  return (
    <section className="rounded-lg border border-deep-moss/15 bg-ink-green p-3 shadow-xl sm:p-4" aria-label="Original source document">
      <div className="mb-3 flex items-center justify-between text-paper-cream">
        <div className="flex items-center gap-2 text-sm font-medium">
          <FileSearch aria-hidden="true" size={17} /> Original IEP · RIV-1001
        </div>
        <div className="flex items-center gap-2">
          <button aria-label="Previous source page" className="grid size-8 place-items-center rounded-md border border-paper-cream/25 disabled:opacity-35" disabled={page <= 1} onClick={() => onPageChange(page - 1)} type="button">
            <ChevronLeft aria-hidden="true" size={16} />
          </button>
          <span className="min-w-16 text-center font-tabular text-xs">{page} / {pageCount}</span>
          <button aria-label="Next source page" className="grid size-8 place-items-center rounded-md border border-paper-cream/25 disabled:opacity-35" disabled={page >= pageCount} onClick={() => onPageChange(page + 1)} type="button">
            <ChevronRight aria-hidden="true" size={16} />
          </button>
        </div>
      </div>
      <div className="relative mx-auto overflow-hidden rounded-[2px] bg-paper-cream">
        <img
          alt={`Rendered page ${page} of Aanya Sharma's original IEP`}
          className="block h-auto w-full"
          src={`/mock/riverside/RIV-1001-page-${page}.png`}
        />
        {highlight !== null ? (
          <div
            aria-label={`Highlighted source quote: ${field.sourceQuote ?? ""}`}
            className="absolute border-2 border-review bg-sand-peach/45 shadow-[0_0_0_2px_color-mix(in_srgb,var(--bl-paper-cream)_70%,transparent)]"
            style={highlight}
          >
            <span className="absolute -top-7 left-0 rounded-[2px] bg-review px-2 py-1 font-mono text-[0.56rem] tracking-wide whitespace-nowrap text-surface uppercase">
              Exact source
            </span>
          </div>
        ) : null}
      </div>
      <div className="mt-3 min-h-14 rounded-[2px] border border-paper-cream/20 px-3 py-2 text-paper-cream">
        <p className="font-mono text-[0.58rem] tracking-[0.1em] text-paper-cream/55 uppercase">
          {field.sourceQuote === null ? "Source limitation" : `Page ${field.sourcePage} · verbatim quote`}
        </p>
        <p className="mt-1 font-serif text-sm leading-5">
          {field.sourceQuote ?? "The v1.2 contract carries confidence for this top-level field but does not expose its page-and-quote anchor."}
        </p>
      </div>
    </section>
  );
}

function highlightPosition(field: ReviewField, page: number): React.CSSProperties | null {
  if (field.sourcePage !== page || field.sourceQuote === null) return null;
  const positions: Record<number, Array<{ top: string; left: string; width: string; height: string }>> = {
    2: [
      { top: "12.2%", left: "7.2%", width: "69%", height: "5.2%" },
      { top: "17.8%", left: "7.2%", width: "69%", height: "5.2%" },
      { top: "23.2%", left: "7.2%", width: "62%", height: "5.2%" },
      { top: "28.7%", left: "7.2%", width: "72%", height: "5.2%" },
      { top: "34.1%", left: "7.2%", width: "62%", height: "5.2%" },
    ],
    3: [{ top: "12%", left: "7.2%", width: "82%", height: "7%" }],
    4: [
      { top: "12%", left: "7.2%", width: "84%", height: "10%" },
      { top: "28%", left: "7.2%", width: "84%", height: "10%" },
      { top: "44%", left: "7.2%", width: "84%", height: "10%" },
    ],
  };
  return positions[page]?.[field.sourceIndex] ?? null;
}
