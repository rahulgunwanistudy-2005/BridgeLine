"""Filesystem-backed Markdown prompt registry."""

import re
from collections.abc import Mapping
from pathlib import Path
from string import Template

_PROMPT_NAME = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


class PromptRegistryError(RuntimeError):
    """Base class for safe prompt registry failures."""


class PromptNotFoundError(PromptRegistryError):
    """Raised when a named Markdown prompt does not exist."""


class PromptRenderError(PromptRegistryError):
    """Raised when required prompt template variables are missing."""


class PromptRegistry:
    """Load and render version-controlled Markdown prompts by safe logical name."""

    def __init__(self, root: Path | None = None) -> None:
        """Use the package prompt directory unless a test or caller supplies one."""

        self._root = root or Path(__file__).with_name("prompts")

    def load(self, name: str) -> str:
        """Load one non-empty `.md` prompt without permitting path traversal."""

        if _PROMPT_NAME.fullmatch(name) is None:
            raise PromptNotFoundError(f"invalid prompt name: {name!r}")
        path = self._root / f"{name}.md"
        try:
            prompt = path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise PromptNotFoundError(f"prompt not found: {name}") from exc
        if not prompt.strip():
            raise PromptRegistryError(f"prompt is empty: {name}")
        return prompt

    def render(self, name: str, variables: Mapping[str, str]) -> str:
        """Substitute explicit `$name` variables in a registered prompt."""

        try:
            return Template(self.load(name)).substitute(variables)
        except KeyError as exc:
            missing = str(exc.args[0])
            raise PromptRenderError(
                f"prompt {name!r} requires missing variable {missing!r}"
            ) from exc
