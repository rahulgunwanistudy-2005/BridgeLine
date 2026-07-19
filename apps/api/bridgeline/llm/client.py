"""Gemini transport gateway with strict structured responses and rate control."""

import asyncio
import logging
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from time import perf_counter
from typing import Literal, TypeVar

from google import genai
from google.genai import errors, types
from httpx import TransportError
from pydantic import BaseModel, SecretStr, ValidationError

from bridgeline.config import Settings

GEMINI_MODEL = "gemini-3.5-flash"
"""Pinned Google AI Studio model identifier verified on 2026-07-19."""

_INPUT_USD_PER_MILLION = Decimal("1.50")
_CACHED_INPUT_USD_PER_MILLION = Decimal("0.15")
_OUTPUT_USD_PER_MILLION = Decimal("9.00")
_ONE_MILLION = Decimal(1_000_000)
_RETRYABLE_STATUS_CODES = frozenset({408, 429, 500, 502, 503, 504})

logger = logging.getLogger(__name__)

StructuredModel = TypeVar("StructuredModel", bound=BaseModel)


class GeminiGatewayError(RuntimeError):
    """Base class for typed Gemini gateway failures."""


class GeminiConfigurationError(GeminiGatewayError):
    """Raised when the gateway cannot be created from application settings."""


class GeminiRequestError(GeminiGatewayError):
    """Raised when Gemini rejects or repeatedly fails a request."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        """Record a safe error message and optional HTTP status code."""

        super().__init__(message)
        self.status_code = status_code


class GeminiResponseError(GeminiGatewayError):
    """Raised when Gemini returns no valid instance of the requested schema."""


@dataclass(frozen=True, slots=True)
class InlineImage:
    """Image bytes embedded directly in a generateContent request."""

    data: bytes
    mime_type: str

    def __post_init__(self) -> None:
        """Reject empty or non-image inline parts before making a network call."""

        if not self.data:
            raise ValueError("inline image data must not be empty")
        if not self.mime_type.startswith("image/"):
            raise ValueError("inline image mime_type must start with 'image/'")


@dataclass(frozen=True, slots=True)
class FileImage:
    """Previously uploaded Gemini Files API image reference."""

    file_uri: str
    mime_type: str

    def __post_init__(self) -> None:
        """Reject incomplete uploaded-file references before generation."""

        if not self.file_uri.strip():
            raise ValueError("file_uri must not be empty")
        if not self.mime_type.startswith("image/"):
            raise ValueError("file image mime_type must start with 'image/'")


ImageInput = InlineImage | FileImage


@dataclass(frozen=True, slots=True)
class CallUsage:
    """Token counts and a standard-list-price estimate for one successful call."""

    prompt_tokens: int
    cached_prompt_tokens: int
    candidate_tokens: int
    thought_tokens: int
    total_tokens: int
    estimated_cost_usd: Decimal


@dataclass(frozen=True, slots=True)
class StructuredResult[ResultModel: BaseModel]:
    """Validated structured payload plus provider accounting metadata."""

    data: ResultModel
    usage: CallUsage
    response_id: str | None
    model_version: str | None


class GeminiGateway:
    """Provider-only Gemini client; domain behavior belongs in caller modules."""

    def __init__(
        self,
        *,
        api_key: SecretStr,
        max_concurrency: int = 1,
        min_interval_seconds: float = 4.1,
        max_attempts: int = 3,
        retry_base_seconds: float = 1.0,
        client: genai.Client | None = None,
    ) -> None:
        """Create a throttled gateway without reading environment variables."""

        if max_concurrency < 1:
            raise ValueError("max_concurrency must be at least 1")
        if min_interval_seconds < 0:
            raise ValueError("min_interval_seconds must not be negative")
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if retry_base_seconds <= 0:
            raise ValueError("retry_base_seconds must be positive")

        self._client = client or genai.Client(api_key=api_key.get_secret_value())
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._start_lock = asyncio.Lock()
        self._last_started_at: float | None = None
        self._min_interval_seconds = min_interval_seconds
        self._max_attempts = max_attempts
        self._retry_base_seconds = retry_base_seconds

    @classmethod
    def from_settings(cls, settings: Settings) -> "GeminiGateway":
        """Build the gateway from validated settings supplied by the app boundary."""

        if settings.google_api_key is None:
            raise GeminiConfigurationError("GOOGLE_API_KEY is required for Gemini calls")
        return cls(
            api_key=settings.google_api_key,
            max_concurrency=settings.llm_max_concurrency,
            min_interval_seconds=settings.llm_min_interval_seconds,
            max_attempts=settings.llm_max_attempts,
            retry_base_seconds=settings.llm_retry_base_seconds,
        )

    async def upload_image(self, path: Path) -> FileImage:
        """Upload a large or reusable local image through Gemini's Files API."""

        async with self._semaphore:
            await self._wait_for_start_slot()
            uploaded = await self._client.aio.files.upload(file=path)

        if uploaded.uri is None or uploaded.mime_type is None:
            raise GeminiResponseError("Gemini Files API returned an incomplete image reference")
        return FileImage(file_uri=uploaded.uri, mime_type=uploaded.mime_type)

    async def generate_structured(
        self,
        *,
        prompt: str,
        response_model: type[StructuredModel],
        images: tuple[ImageInput, ...] = (),
        max_output_tokens: int = 4096,
        temperature: float | None = None,
        thinking_level: Literal["minimal", "low", "medium", "high"] = "minimal",
    ) -> StructuredResult[StructuredModel]:
        """Generate and locally revalidate one JSON-schema-constrained response."""

        if not prompt.strip():
            raise ValueError("prompt must not be empty")
        if max_output_tokens < 1:
            raise ValueError("max_output_tokens must be at least 1")

        parts = [types.Part.from_text(text=prompt)]
        parts.extend(self._image_part(image) for image in images)
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_json_schema=response_model.model_json_schema(),
            max_output_tokens=max_output_tokens,
            temperature=temperature,
            thinking_config=types.ThinkingConfig(thinking_level=thinking_level),
        )

        response, attempt, latency_ms = await self._request_with_retry(parts, config)
        raw_text = response.text
        if raw_text is None:
            raise GeminiResponseError("Gemini returned no text for a structured response")

        try:
            data = response_model.model_validate_json(raw_text)
        except ValidationError as exc:
            raise GeminiResponseError("Gemini response failed local Pydantic validation") from exc

        usage = self._usage(response.usage_metadata)
        logger.info(
            "llm_call model=%s attempt=%d latency_ms=%d prompt_tokens=%d "
            "cached_prompt_tokens=%d candidate_tokens=%d thought_tokens=%d "
            "total_tokens=%d estimated_standard_cost_usd=%s",
            GEMINI_MODEL,
            attempt,
            latency_ms,
            usage.prompt_tokens,
            usage.cached_prompt_tokens,
            usage.candidate_tokens,
            usage.thought_tokens,
            usage.total_tokens,
            usage.estimated_cost_usd,
        )
        return StructuredResult(
            data=data,
            usage=usage,
            response_id=response.response_id,
            model_version=response.model_version,
        )

    async def _request_with_retry(
        self,
        parts: list[types.Part],
        config: types.GenerateContentConfig,
    ) -> tuple[types.GenerateContentResponse, int, int]:
        """Retry only transient provider failures using bounded exponential backoff."""

        for attempt in range(1, self._max_attempts + 1):
            started_at = perf_counter()
            try:
                async with self._semaphore:
                    await self._wait_for_start_slot()
                    response = await self._client.aio.models.generate_content(
                        model=GEMINI_MODEL,
                        contents=parts,
                        config=config,
                    )
                latency_ms = round((perf_counter() - started_at) * 1000)
                return response, attempt, latency_ms
            except errors.APIError as exc:
                retryable = exc.code in _RETRYABLE_STATUS_CODES
                if not retryable or attempt == self._max_attempts:
                    raise GeminiRequestError(
                        "Gemini generateContent request failed",
                        status_code=exc.code,
                    ) from exc
                delay = self._retry_base_seconds * (2 ** (attempt - 1))
                logger.warning(
                    "llm_retry model=%s attempt=%d status_code=%d delay_seconds=%.2f",
                    GEMINI_MODEL,
                    attempt,
                    exc.code,
                    delay,
                )
                await asyncio.sleep(delay)
            except TransportError as exc:
                if attempt == self._max_attempts:
                    raise GeminiRequestError("Gemini network request failed") from exc
                delay = self._retry_base_seconds * (2 ** (attempt - 1))
                logger.warning(
                    "llm_retry model=%s attempt=%d reason=transport delay_seconds=%.2f",
                    GEMINI_MODEL,
                    attempt,
                    delay,
                )
                await asyncio.sleep(delay)

        raise AssertionError("retry loop exited without returning or raising")

    async def _wait_for_start_slot(self) -> None:
        """Serialize request starts and preserve the configured minimum interval."""

        loop = asyncio.get_running_loop()
        async with self._start_lock:
            now = loop.time()
            if self._last_started_at is not None:
                remaining = self._min_interval_seconds - (now - self._last_started_at)
                if remaining > 0:
                    await asyncio.sleep(remaining)
            self._last_started_at = loop.time()

    @staticmethod
    def _image_part(image: ImageInput) -> types.Part:
        """Convert supported inline and Files API image inputs into Gemini parts."""

        if isinstance(image, InlineImage):
            return types.Part.from_bytes(data=image.data, mime_type=image.mime_type)
        return types.Part.from_uri(file_uri=image.file_uri, mime_type=image.mime_type)

    @staticmethod
    def _usage(metadata: types.GenerateContentResponseUsageMetadata | None) -> CallUsage:
        """Normalize Gemini usage metadata and estimate current standard list cost."""

        if metadata is None:
            raise GeminiResponseError("Gemini response omitted token usage metadata")
        prompt_tokens = metadata.prompt_token_count or 0
        cached_tokens = metadata.cached_content_token_count or 0
        candidate_tokens = metadata.candidates_token_count or 0
        thought_tokens = metadata.thoughts_token_count or 0
        total_tokens = metadata.total_token_count or (
            prompt_tokens + candidate_tokens + thought_tokens
        )
        uncached_tokens = max(prompt_tokens - cached_tokens, 0)
        estimated_cost = (
            Decimal(uncached_tokens) * _INPUT_USD_PER_MILLION
            + Decimal(cached_tokens) * _CACHED_INPUT_USD_PER_MILLION
            + Decimal(candidate_tokens + thought_tokens) * _OUTPUT_USD_PER_MILLION
        ) / _ONE_MILLION
        return CallUsage(
            prompt_tokens=prompt_tokens,
            cached_prompt_tokens=cached_tokens,
            candidate_tokens=candidate_tokens,
            thought_tokens=thought_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=estimated_cost.quantize(Decimal("0.000000001")),
        )
