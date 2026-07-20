"""Generate reviewer-readable rule documentation from the immutable registry."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from bridgeline.rules.registry import RULES, RULES_VERSION

RULES_PATH = Path(__file__).with_name("RULES.md")


def render_rules_markdown() -> str:
    """Render every registered rule in canonical registry order."""

    sections = [
        "# Compliance Rules Registry",
        "",
        "This file is generated from `bridgeline.rules.registry`. Do not edit it by hand.",
        "",
        (
            "Citations are sourced from "
            "[`references/idea-citations.md`](../../../../references/idea-citations.md) and "
            "verified against Cornell LII and eCFR."
        ),
        "",
        f"Rules version: `{RULES_VERSION}`",
        "",
    ]
    for rule in RULES:
        sections.extend(
            (
                f"## `{rule.id}`",
                "",
                f"- Citation: [`{rule.citation}`]({_cornell_url(rule.citation)})",
                f"- Description: {rule.description}",
                "",
            )
        )
    return "\n".join(sections)


def _cornell_url(citation: str) -> str:
    match = re.fullmatch(r"34 CFR §(?P<section>\d+\.\d+)(?:\(.*\))?", citation)
    if match is None:
        raise ValueError(f"cannot generate Cornell URL for citation {citation!r}")
    return f"https://www.law.cornell.edu/cfr/text/34/{match.group('section')}"


def write_or_check(*, check: bool) -> None:
    """Write the generated document or fail if the committed copy drifted."""

    rendered = render_rules_markdown()
    if check:
        if not RULES_PATH.exists() or RULES_PATH.read_text(encoding="utf-8") != rendered:
            raise SystemExit(
                "rules/RULES.md is stale; run python -m bridgeline.rules.generate_docs"
            )
        return
    RULES_PATH.write_text(rendered, encoding="utf-8")


def main() -> None:
    """Run the generator CLI."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    write_or_check(check=arguments.check)


if __name__ == "__main__":
    main()
