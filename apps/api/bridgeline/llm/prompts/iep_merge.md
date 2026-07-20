Merge these independently extracted IEP sections into one response.

Preserve every VERBATIM source_quote and source_page. Deduplicate only formatting-identical items
that point to the same approval. Resolve no conflict by guessing: return null with confidence 0.
For scalar fields, prefer the value with direct source evidence and the lowest confidence whenever
conflicting drafts cannot be reconciled. Never average or inflate confidence during the merge.
Preserve each accommodation scope reference with its own verbatim ref, source page, source quote,
and confidence. Never merge accommodations that have identical text but different scope
fingerprints. Never broaden a qualified scope to `all`; `all` is reserved for explicit,
unconstrained language such as “across all classes.”

$drafts
