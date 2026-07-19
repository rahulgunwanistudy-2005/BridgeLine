"""Provider gateway and prompt registry for structured model calls."""

from bridgeline.llm.client import (
    GEMINI_MODEL,
    FileImage,
    GeminiGateway,
    InlineImage,
    StructuredResult,
)
from bridgeline.llm.prompts import PromptRegistry

__all__ = [
    "GEMINI_MODEL",
    "FileImage",
    "GeminiGateway",
    "InlineImage",
    "PromptRegistry",
    "StructuredResult",
]
