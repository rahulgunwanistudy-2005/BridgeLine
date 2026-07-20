"""Generated registry documentation drift tests."""

from bridgeline.rules.generate_docs import (
    RULES_PATH,
    _cornell_url,
    render_rules_markdown,
    write_or_check,
)
from bridgeline.rules.registry import RULES


def test_rules_markdown_is_committed_and_current() -> None:
    write_or_check(check=True)


def test_rules_markdown_preserves_registry_order() -> None:
    rendered = render_rules_markdown()
    positions = [rendered.index(f"## `{rule.id}`") for rule in RULES]

    assert positions == sorted(positions)
    assert RULES_PATH.read_text(encoding="utf-8") == rendered


def test_every_citation_links_to_its_cornell_section() -> None:
    rendered = render_rules_markdown()

    assert all(f"[`{rule.citation}`]({_cornell_url(rule.citation)})" in rendered for rule in RULES)
