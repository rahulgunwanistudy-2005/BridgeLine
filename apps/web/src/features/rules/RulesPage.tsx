import { AlertOctagon, BookOpen, RefreshCw, Scale } from "lucide-react";
import { useEffect, useState } from "react";

import { CitationChip } from "../../components/CitationChip";
import { apiClient } from "../../lib/api/client";
import { cornellCitationUrl } from "../../lib/citations";
import type { RegistryResponse } from "../../lib/api/contracts";
import "./rules.css";

export function RulesPage(): React.JSX.Element {
  const [registry, setRegistry] = useState<RegistryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiClient.rules().then(setRegistry).catch((cause: unknown) => setError(cause instanceof Error ? cause.message : "The rule registry could not be loaded."));
  }, []);

  if (error !== null) {
    return <main className="rules-page"><section className="rules-error"><AlertOctagon size={24} /><h1>The verification register did not load.</h1><p>{error}</p><button onClick={() => window.location.reload()} type="button"><RefreshCw size={15} /> Retry registry</button></section></main>;
  }

  return (
    <main className="rules-page">
      <header className="rules-header">
        <div><p className="rules-kicker"><Scale size={14} /> Deterministic rule registry</p><h1>Every operational duty has a legal source.</h1><p>Generated from the code registry in stable order. Citations are sourced from <code>references/idea-citations.md</code> and verified against Cornell LII and eCFR.</p></div>
        <div className="rules-seal"><span>{registry?.rules.length ?? "—"}</span><small>registered rules</small><small>{registry?.rules_version ?? "Loading version"}</small></div>
      </header>
      {registry === null ? <RulesSkeleton /> : registry.rules.length === 0 ? <section className="rules-empty"><BookOpen size={24} /><h2>No rules are registered yet.</h2><p>Add a cited rule to the deterministic registry, then regenerate this verification view.</p></section> : (
        <ol className="rules-register">
          {registry.rules.map((rule, index) => (
            <li className="rules-row" key={rule.id}>
              <span className="rules-number">{String(index + 1).padStart(2, "0")}</span>
              <div><h2>{rule.id}</h2><p>{rule.description}</p></div>
              <CitationChip citation={rule.citation} description={rule.description} href={cornellCitationUrl(rule.citation)} />
            </li>
          ))}
        </ol>
      )}
      <footer className="rules-footer"><p>Registry content is generated; interface copy does not alter citations or rule descriptions.</p><a href="https://www.ecfr.gov/current/title-34/subtitle-B/chapter-III/part-300" rel="noreferrer" target="_blank">Cross-check Title 34 in eCFR</a></footer>
    </main>
  );
}

function RulesSkeleton(): React.JSX.Element { return <div className="rules-register" aria-label="Loading rule registry">{Array.from({ length: 5 }, (_, index) => <div className="rules-row rules-row--loading" key={index}><span /><span /><span /></div>)}</div>; }
