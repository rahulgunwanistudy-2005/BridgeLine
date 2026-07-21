"""Verify that canonical source evidence exists verbatim on its declared PDF page."""

from __future__ import annotations

from typing import Any

import fitz

from synthgen.render import render_pdf


def _normalized(value: str) -> str:
    """Collapse layout whitespace while preserving exact case and wording."""

    return " ".join(value.split())


def evidence_problems(record: dict[str, Any]) -> list[str]:
    """Return evidence/page mismatches for one record's deterministic clean render."""

    problems: list[str] = []
    with fitz.open(stream=render_pdf(record), filetype="pdf") as document:
        expected_pages = record["extraction_meta"]["page_count"]
        if len(document) != expected_pages:
            problems.append(
                f"{record['student_ref']}: rendered {len(document)} pages; expected {expected_pages}"
            )
        page_text = [_normalized(page.get_text()) for page in document]

    for collection in ("accommodations", "services", "goals"):
        for index, item in enumerate(record[collection]):
            _check_quote(
                problems,
                record["student_ref"],
                f"{collection}[{index}]",
                item["source_page"],
                item["source_quote"],
                page_text,
            )
            if collection == "accommodations":
                for ref_index, reference in enumerate(item["applies_to_refs"]):
                    _check_quote(
                        problems,
                        record["student_ref"],
                        f"{collection}[{index}].applies_to_refs[{ref_index}]",
                        reference["source_page"],
                        reference["source_quote"],
                        page_text,
                    )
    return problems


def _check_quote(
    problems: list[str],
    student_ref: str,
    path: str,
    source_page: int,
    source_quote: str,
    page_text: list[str],
) -> None:
    if not 1 <= source_page <= len(page_text):
        problems.append(f"{student_ref}: {path} source_page {source_page} does not exist")
        return
    if _normalized(source_quote) not in page_text[source_page - 1]:
        problems.append(
            f"{student_ref}: {path} quote absent from page {source_page}: {source_quote!r}"
        )
