PAGE_NUMBER=$page_number

You are correcting OCR for one IEP page. Use the page image as primary evidence, then compare the
raw OCR and any embedded PDF text. Preserve document order, headings, table rows, handwriting,
margin notes, stamps, and signatures. Do not paraphrase and do not add text that is not visible.
Represent unreadable spans as `[illegible]`. For a two-column layout, finish the left column before
the right unless visual structure clearly indicates another reading order. Return corrected text and
a legibility score from 0 (unreadable) to 1 (fully legible).

EMBEDDED_TEXT:
$embedded_text

RAW_OCR_TEXT:
$ocr_text
