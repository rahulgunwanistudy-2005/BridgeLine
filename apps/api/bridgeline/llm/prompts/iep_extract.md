Extract the following IEP pages into the response schema.

Safety contract:

1. Extract VERBATIM evidence first. Every accommodation, service, and goal must carry the exact
   `source_quote` and one-based `source_page` that jointly support every normalized value.
2. THEN normalize only mechanical representations: ISO dates, weekly service minutes, and obvious
   OCR spacing. Do not paraphrase approved accommodation or goal language.
3. NEVER invent a value. If the document does not state a field, return null and assign its matching
   field confidence 0 in the `field_confidences` object. Low legibility, handwriting,
   stamps/signatures over text,
   or conflicting passages must lower confidence; uncertainty is not permission to guess.
4. Populate every required property in the `field_confidences` object: `student_ref`,
   `disability_category`, `school_year`, `annual_review`, `triennial_reeval`, and
   `last_progress_report`. These confidence properties correspond to the same-named top-level
   fields and date fields in the extracted record.
5. Read two-column layouts in visual order. Preserve handwritten margin notes. Reconstruct a
   service-minute table row before normalizing frequency into total weekly minutes.
6. Keep repeated wording as separate only when separate source anchors show distinct approvals.
7. Dates may use mixed source formats; normalize only unambiguous dates to YYYY-MM-DD.
8. For every accommodation, extract `applies_to_refs` from the document wording itself. Each
   reference must contain its own `scope`, verbatim `ref`, `source_page`, `source_quote`, and
   `confidence`. Never emit district course codes or infer a scope from roster data.
9. Scope references within the same scope are alternatives. Subject and context scopes together
   mean intersection: the accommodation applies only where both constraints hold. If the document
   instead states separate alternatives, preserve them as separately anchored accommodation
   clauses. Do not merge their scope fingerprints merely because their accommodation text matches.
10. Use `scope: "all"` only when the IEP states genuinely unconstrained applicability, such as
    “in all settings” or “across all classes.” `all` means no subject or context constraint. Any
    qualifier—including “all academic subjects,” “core classes,” or “general education
    settings”—makes the reference a subject or context scope, never `all`. If a qualified phrase
    cannot be resolved to subjects explicitly enumerated in the document, preserve the phrase,
    lower its confidence, and let human review resolve it. Never default missing or ambiguous
    scope to `all`.

$pages
