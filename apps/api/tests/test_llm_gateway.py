"""Unit tests for Gemini transport behavior and prompt loading."""

from decimal import Decimal
from pathlib import Path
from typing import cast

import pytest
from google import genai
from google.genai import types
from pydantic import BaseModel, ConfigDict, SecretStr

from bridgeline.llm.client import GeminiGateway, InlineImage
from bridgeline.llm.prompts import PromptNotFoundError, PromptRegistry, PromptRenderError


class ExamplePayload(BaseModel):
    """Small schema used to exercise the generic response boundary."""

    model_config = ConfigDict(extra="forbid")

    answer: str


class FakeModels:
    """Capture one generateContent call and return a provider-shaped response."""

    def __init__(self) -> None:
        self.model: str | None = None
        self.config: types.GenerateContentConfig | None = None

    async def generate_content(
        self,
        *,
        model: str,
        contents: object,
        config: types.GenerateContentConfig,
    ) -> types.GenerateContentResponse:
        """Return JSON text and usage metadata without provider I/O."""

        del contents
        self.model = model
        self.config = config
        return types.GenerateContentResponse(
            candidates=[
                types.Candidate(
                    content=types.Content(
                        role="model",
                        parts=[types.Part.from_text(text='{"answer":"validated"}')],
                    )
                )
            ],
            usage_metadata=types.GenerateContentResponseUsageMetadata(
                prompt_token_count=3,
                candidates_token_count=2,
                total_token_count=5,
            ),
            response_id="response-1",
            model_version="gemini-3.5-flash",
        )


class FakeAsyncClient:
    """Expose the SDK's asynchronous models namespace."""

    def __init__(self, models: FakeModels) -> None:
        self.models = models


class FakeClient:
    """Small structural test double for the Google Gen AI client."""

    def __init__(self, models: FakeModels) -> None:
        self.aio = FakeAsyncClient(models)


def test_prompt_registry_loads_and_renders_markdown(tmp_path: Path) -> None:
    """Registered prompts load by name and require all declared variables."""

    (tmp_path / "example.md").write_text("Hello, $audience!", encoding="utf-8")
    registry = PromptRegistry(tmp_path)

    assert registry.load("example") == "Hello, $audience!"
    assert registry.render("example", {"audience": "team"}) == "Hello, team!"

    with pytest.raises(PromptRenderError):
        registry.render("example", {})


def test_prompt_registry_blocks_path_traversal(tmp_path: Path) -> None:
    """Logical prompt names cannot escape the configured prompt directory."""

    with pytest.raises(PromptNotFoundError):
        PromptRegistry(tmp_path).load("../secret")


def test_inline_image_rejects_non_image_mime_type() -> None:
    """Invalid image parts fail before provider I/O."""

    with pytest.raises(ValueError, match="mime_type"):
        InlineImage(data=b"bytes", mime_type="application/pdf")


async def test_generate_structured_uses_schema_and_revalidates_response() -> None:
    """The gateway sends Gemini schema controls and returns a Pydantic instance."""

    models = FakeModels()
    gateway = GeminiGateway(
        api_key=SecretStr("test-key"),
        min_interval_seconds=0,
        client=cast(genai.Client, FakeClient(models)),
    )

    result = await gateway.generate_structured(
        prompt="Return a value.",
        response_model=ExamplePayload,
    )

    assert result.data == ExamplePayload(answer="validated")
    assert models.model == "gemini-3.5-flash"
    assert models.config is not None
    assert models.config.response_mime_type == "application/json"
    assert models.config.response_json_schema == ExamplePayload.model_json_schema()


def test_usage_includes_thinking_tokens_at_output_price() -> None:
    """Cost estimates follow Gemini 3.5 Flash standard list pricing."""

    metadata = types.GenerateContentResponseUsageMetadata(
        prompt_token_count=100,
        cached_content_token_count=20,
        candidates_token_count=10,
        thoughts_token_count=5,
        total_token_count=115,
    )

    usage = GeminiGateway._usage(metadata)

    assert usage.prompt_tokens == 100
    assert usage.thought_tokens == 5
    assert usage.estimated_cost_usd == Decimal("0.000258000")


def test_gateway_defaults_accept_one_concurrent_request() -> None:
    """The temporary free-tier safety default constructs without broad concurrency."""

    gateway = GeminiGateway(api_key=SecretStr("test-key"), min_interval_seconds=0)

    assert gateway._semaphore._value == 1
