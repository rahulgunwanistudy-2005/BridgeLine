"""Tesseract OCR followed by schema-validated Gemini page cleanup."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from io import BytesIO
from typing import Literal, Protocol, TypeVar

import pytesseract
from PIL import Image
from pydantic import BaseModel, ConfigDict, Field

from bridgeline.ingest.normalize import NormalizedDocument, NormalizedPage
from bridgeline.llm.client import ImageInput, InlineImage, StructuredResult
from bridgeline.llm.prompts import PromptRegistry

StructuredModel = TypeVar("StructuredModel", bound=BaseModel)


class StructuredGateway(Protocol):
    """Narrow gateway surface used by ingest stages and test doubles."""

    async def generate_structured(
        self,
        *,
        prompt: str,
        response_model: type[StructuredModel],
        images: tuple[ImageInput, ...] = (),
        max_output_tokens: int = 4096,
        temperature: float | None = None,
        thinking_level: Literal["minimal", "low", "medium", "high"] = "minimal",
    ) -> StructuredResult[StructuredModel]: ...


class PageCleanup(BaseModel):
    """Validated cleanup response for one page."""

    model_config = ConfigDict(extra="forbid", strict=True)

    corrected_text: str = Field(min_length=1)
    legibility_score: float = Field(ge=0.0, le=1.0)


class OCRPage(BaseModel):
    """One page of source-preserving cleaned text."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    page_number: int = Field(ge=1)
    raw_ocr_text: str
    embedded_text: str | None
    corrected_text: str = Field(min_length=1)
    legibility_score: float = Field(ge=0.0, le=1.0)


class OCRProcessor:
    """Bounded per-page OCR and visual cleanup."""

    def __init__(
        self,
        *,
        gateway: StructuredGateway,
        page_concurrency: int = 1,
        tesseract_runner: Callable[[bytes], str] | None = None,
        prompts: PromptRegistry | None = None,
    ) -> None:
        self._gateway = gateway
        # Gemini's free-tier quota makes two the safety ceiling regardless of caller config.
        self._semaphore = asyncio.Semaphore(min(max(page_concurrency, 1), 2))
        self._tesseract = tesseract_runner or _run_tesseract
        self._prompts = prompts or PromptRegistry()

    async def process(self, document: NormalizedDocument) -> tuple[OCRPage, ...]:
        """Process all pages concurrently while retaining deterministic page order."""

        pages = await asyncio.gather(*(self._process_page(page) for page in document.pages))
        return tuple(sorted(pages, key=lambda page: page.page_number))

    async def _process_page(self, page: NormalizedPage) -> OCRPage:
        async with self._semaphore:
            raw_text = (
                await asyncio.to_thread(self._tesseract, page.image_png)
                if page.image_png is not None
                else ""
            )
            prompt = self._prompts.render(
                "ocr_cleanup",
                {
                    "page_number": str(page.number),
                    "embedded_text": page.embedded_text or "NO_EMBEDDED_TEXT",
                    "ocr_text": raw_text or "NO_OCR_TEXT",
                },
            )
            images = (
                (InlineImage(data=page.image_png, mime_type="image/png"),)
                if page.image_png is not None
                else ()
            )
            result = await self._gateway.generate_structured(
                prompt=prompt,
                response_model=PageCleanup,
                images=images,
                max_output_tokens=4096,
                temperature=0.0,
                thinking_level="minimal",
            )
            cleanup = result.data
            return OCRPage(
                page_number=page.number,
                raw_ocr_text=raw_text,
                embedded_text=page.embedded_text,
                corrected_text=cleanup.corrected_text,
                legibility_score=cleanup.legibility_score,
            )


def _run_tesseract(image_png: bytes) -> str:
    image = Image.open(BytesIO(image_png))
    return str(pytesseract.image_to_string(image, config="--oem 3 --psm 3")).strip()
