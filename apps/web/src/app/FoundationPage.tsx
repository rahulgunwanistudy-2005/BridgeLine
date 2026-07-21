import { ArrowRight, FileCheck2, Play, ShieldCheck } from "lucide-react";
import { Link } from "react-router-dom";

import { CitationChip } from "../components/CitationChip";
import { TransferSpine } from "../components/TransferSpine";
import "./foundation.css";

export function FoundationPage(): React.JSX.Element {
  return (
    <div className="foundation-page">
      <header className="foundation-header">
        <Link className="foundation-brand" to="/"><span><FileCheck2 aria-hidden="true" size={19} /></span>Bridgeline</Link>
        <div className="foundation-district"><ShieldCheck aria-hidden="true" size={16} /> Riverside Demo District</div>
      </header>

      <main className="foundation-hero">
        <div className="foundation-title" aria-labelledby="foundation-hook">
          <p>Finalized does not mean delivered</p>
          <h1 id="foundation-hook"><span>An IEP can be final</span><span>and still never reach</span><span>the classroom.</span></h1>
        </div>

        <div className="foundation-object"><TransferSpine /></div>

        <aside className="foundation-explanation">
          <p>Bridgeline carries every verified duty from its source page to the person responsible—and shows whether it actually arrived.</p>
          <div className="foundation-actions">
            <Link className="foundation-enter" to="/upload">Enter the product <ArrowRight size={16} /></Link>
            <Link className="foundation-judge" to="/judge"><Play fill="currentColor" size={14} /> Start Judge Mode</Link>
          </div>
        </aside>

        <div className="foundation-citation">
          <span>THE DUTY</span>
          <CitationChip citation="34 CFR §300.323(d)(2)(ii)" description="Teachers and providers must be informed of the specific accommodations, modifications, and supports they must provide." href="https://www.law.cornell.edu/cfr/text/34/300.323" />
        </div>
      </main>

      <section className="foundation-after" aria-label="Bridgeline workflow">
        <p>Document</p><span>Evidence</span><span>Human verified</span><span>Cited duty</span><span>Responsible person</span><strong>Confirmation</strong>
      </section>
    </div>
  );
}
