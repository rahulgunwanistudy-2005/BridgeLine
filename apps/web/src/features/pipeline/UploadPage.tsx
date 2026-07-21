import { FileText, ShieldCheck, UploadCloud } from "lucide-react";
import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { apiClient } from "../../lib/api/client";

export function UploadPage(): React.JSX.Element {
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(file: File): Promise<void> {
    setUploading(true);
    setError(null);
    try {
      const response = await apiClient.upload(file);
      navigate(`/runs/${response.run_id}`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The IEP could not be uploaded.");
      setUploading(false);
    }
  }

  function useRiversideSample(): void {
    const sample = new File(["Riverside source fixture"], "RIV-1001-clean-sample-iep.pdf", {
      type: "application/pdf",
    });
    void submit(sample);
  }

  return (
    <main className="mx-auto max-w-6xl px-4 py-10 sm:px-6 lg:px-8 lg:py-16">
      <div className="grid gap-10 lg:grid-cols-[0.72fr_1.28fr] lg:items-start">
        <section>
          <p className="font-mono text-xs tracking-[0.12em] text-deep-moss uppercase">New record</p>
          <h1 className="mt-4 max-w-md text-4xl leading-tight font-semibold tracking-[-0.03em]">
            Start with the document. Keep every duty tied to its source.
          </h1>
          <p className="mt-5 max-w-md leading-7 text-ink-green/70">
            Bridgeline prepares the pages, extracts a typed draft, and pauses for your review
            before any responsibility is derived.
          </p>
          <div className="mt-8 grid gap-3 text-sm text-ink-green/70">
            <p className="flex items-center gap-3"><ShieldCheck aria-hidden="true" size={18} /> Nothing becomes operational truth without approval.</p>
            <p className="flex items-center gap-3"><FileText aria-hidden="true" size={18} /> Source page and exact quote stay attached.</p>
          </div>
        </section>

        <section
          className={`rounded-lg border-2 border-dashed bg-surface p-6 transition-colors sm:p-10 ${dragging ? "border-deep-moss bg-paper-cream" : "border-deep-moss/25"}`}
          onDragEnter={(event) => { event.preventDefault(); setDragging(true); }}
          onDragLeave={(event) => { event.preventDefault(); setDragging(false); }}
          onDragOver={(event) => event.preventDefault()}
          onDrop={(event) => {
            event.preventDefault();
            setDragging(false);
            const file = event.dataTransfer.files.item(0);
            if (file !== null) void submit(file);
          }}
        >
          <div className="grid min-h-72 place-items-center text-center">
            <div>
              <span className="mx-auto grid size-16 place-items-center rounded-full bg-deep-moss text-paper-cream">
                <UploadCloud aria-hidden="true" size={27} />
              </span>
              <h2 className="mt-5 text-xl font-semibold">Drop a finalized IEP here</h2>
              <p className="mx-auto mt-2 max-w-sm text-sm leading-6 text-ink-green/60">
                PDF, DOCX, or page images. The original source stays connected to every
                extracted field.
              </p>
              <div className="mt-6 flex flex-wrap justify-center gap-3">
                <button
                  className="rounded-lg bg-deep-moss px-5 py-3 text-sm font-medium text-paper-cream disabled:opacity-60"
                  disabled={uploading}
                  onClick={() => inputRef.current?.click()}
                  type="button"
                >
                  {uploading ? "Preparing run…" : "Choose document"}
                </button>
                <button
                  className="rounded-lg border border-deep-moss/30 px-5 py-3 text-sm font-medium disabled:opacity-60"
                  disabled={uploading}
                  onClick={useRiversideSample}
                  type="button"
                >
                  Use Riverside sample
                </button>
              </div>
              <input
                accept=".pdf,.docx,image/*"
                className="sr-only"
                onChange={(event) => {
                  const file = event.currentTarget.files?.item(0);
                  if (file !== null && file !== undefined) void submit(file);
                }}
                ref={inputRef}
                type="file"
              />
              {error !== null ? (
                <p className="mt-5 rounded-lg border border-finding/25 bg-finding/5 p-3 text-sm text-finding" role="alert">
                  {error} Check the document and try again.
                </p>
              ) : null}
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
