"""Strict parser for the human-owned IDEA citation specification."""

from __future__ import annotations


class CitationSpecError(ValueError):
    """The citation source does not contain a complete rule/citation pair."""


def parse_citations(text: str) -> dict[str, str]:
    """Return exact CITE values keyed by the stable leading RULE identifier."""

    citations: dict[str, str] = {}
    pending_rule: str | None = None
    for line in text.splitlines():
        if line.startswith("RULE: "):
            pending_rule = line.removeprefix("RULE: ").split(maxsplit=1)[0]
        elif line.startswith("CITE: ") and pending_rule is not None:
            if pending_rule in citations:
                raise CitationSpecError(f"duplicate citation rule {pending_rule}")
            citations[pending_rule] = line.removeprefix("CITE: ")
            pending_rule = None
    if pending_rule is not None:
        raise CitationSpecError(f"rule {pending_rule} has no CITE line")
    return citations
