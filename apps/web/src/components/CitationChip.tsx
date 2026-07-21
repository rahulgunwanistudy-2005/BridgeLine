import { ExternalLink } from "lucide-react";

export interface CitationChipProps {
  citation: string;
  description: string;
  href: string;
}

const CITATION_PATTERN = /^(\d+ CFR) §([\d.]+)(.*)$/;

export function CitationChip({
  citation,
  description,
  href,
}: CitationChipProps): React.JSX.Element {
  const match = CITATION_PATTERN.exec(citation);
  const title = match?.[1] ?? "Federal rule";
  const section = match?.[2] ?? citation;
  const path = match?.[3] ?? "";
  const clauses = path.match(/\([^)]+\)/g) ?? [];

  return (
    <span className="citation-chip group relative inline-flex max-w-full">
      <a
        aria-label={`${citation}. Open regulation on Cornell Legal Information Institute.`}
        className="citation-chip__plate inline-flex min-h-12 max-w-full items-stretch overflow-hidden rounded-[2px] border border-deep-moss bg-paper-cream text-ink-green"
        href={href}
        rel="noreferrer"
        target="_blank"
      >
        <span className="grid w-11 shrink-0 place-items-center bg-deep-moss font-serif text-[1.65rem] leading-none text-paper-cream">
          §
        </span>
        <span className="flex min-w-0 items-center gap-2 px-3 py-1.5 font-mono tabular-nums">
          <span className="flex flex-col leading-none">
            <span className="mb-1 text-[0.58rem] font-medium tracking-[0.12em] uppercase opacity-65">
              {title}
            </span>
            <span className="text-sm font-medium">{section}</span>
          </span>
          {clauses.length > 0 ? (
            <span className="citation-chip__clauses flex items-center text-xs" aria-hidden="true">
              {clauses.map((clause, index) => (
                <span className="border-l border-warm-stone px-1.5" key={`${clause}-${index}`}>
                  {clause}
                </span>
              ))}
            </span>
          ) : null}
          <ExternalLink aria-hidden="true" className="ml-1 shrink-0 opacity-55" size={13} />
        </span>
      </a>
      <span
        className="pointer-events-none absolute top-[calc(100%+0.45rem)] left-0 z-20 hidden w-[min(22rem,80vw)] rounded-[2px] border border-warm-stone bg-paper-cream p-3 font-serif text-sm leading-5 shadow-lg group-focus-within:block group-hover:block"
        role="tooltip"
      >
        {description}
      </span>
    </span>
  );
}
