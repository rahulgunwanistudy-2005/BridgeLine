# Ingest engine design and validation status

The cx/01 pipeline uses typed stage boundaries:

1. `NormalizedDocument` contains ordered page images and any embedded text.
2. `OCRPage` contains raw OCR, corrected text, and page legibility.
3. `ExtractionOutput` contains a schema-valid `IEPRecord`, including its required scalar
   `field_confidences` object.
4. Deterministic identity reconciliation carries stable item IDs forward before `GateResult`
   evaluates extraction, legibility, and ambiguous-match confidence.
5. `IngestStore` persists immutable drafts, while `StatusEventBus` emits contract-valid stage
   events. The current logging implementation is intentionally replaceable by cx/03's
   persist-then-fan-out bus.

The extraction prompt is verbatim-first: it requires source page and quote evidence before any
normalization, represents absent values as null with confidence zero, and prohibits invented
values. Since required canonical `IEPRecord` scalar fields cannot be null, an incomplete LLM draft
stops with a typed review error instead of being padded with a placeholder.

Confidence thresholds are application settings and enforced in code. Any low item confidence,
low scalar confidence, low page legibility, or ambiguous identity produces an explicit review
path. A document is hard-rejected as non-IEP only when the separate classifier is both negative
and above the configured rejection confidence.

Threshold calibration is deliberately deferred until cc/02 supplies the 100-document synthetic
set and five degraded scans. The mechanism and conservative defaults are implemented now; the
95% field-accuracy and zero silent-wrong high-confidence acceptance checks cannot be claimed until
those fixtures and cc/03 ground-truth harness exist.
