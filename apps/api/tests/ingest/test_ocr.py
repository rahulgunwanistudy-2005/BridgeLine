"""Tests for OCR fan-out, cleanup, and mixed-source pages."""

import asyncio
from dataclasses import dataclass
from typing import Any

from bridgeline.ingest.normalize import NormalizedDocument, NormalizedPage
from bridgeline.ingest.ocr import OCRProcessor, PageCleanup
from bridgeline.llm.client import StructuredResult


@dataclass
class TrackingGateway:
    """Gateway double that records the processor's own concurrency bound."""

    active: int = 0
    maximum: int = 0

    async def generate_structured(self, **kwargs: Any) -> StructuredResult[Any]:
        self.active += 1
        self.maximum = max(self.maximum, self.active)
        await asyncio.sleep(0.01)
        response_model = kwargs["response_model"]
        page_number = int(kwargs["prompt"].split("PAGE_NUMBER=")[1].splitlines()[0])
        self.active -= 1
        return StructuredResult(
            data=response_model(
                corrected_text=f"corrected page {page_number}", legibility_score=0.9
            ),
            usage=None,  # type: ignore[arg-type]
            response_id=None,
            model_version="test",
        )


async def test_page_cleanup_concurrency_is_hard_capped_at_two() -> None:
    """A caller cannot accidentally burst beyond the Gemini free-tier budget."""

    gateway = TrackingGateway()
    document = NormalizedDocument(
        filename="mixed.pdf",
        media_type="application/pdf",
        pages=tuple(
            NormalizedPage(number=number, image_png=b"png", embedded_text=None)
            for number in range(1, 7)
        ),
    )
    processor = OCRProcessor(
        gateway=gateway,
        page_concurrency=20,
        tesseract_runner=lambda _image: "raw OCR",
    )

    pages = await processor.process(document)

    assert gateway.maximum == 2
    assert [page.page_number for page in pages] == list(range(1, 7))


async def test_mixed_clean_and_scanned_pages_keep_both_text_sources() -> None:
    """Embedded PDF text and OCR text are both supplied to cleanup."""

    prompts: list[str] = []

    class Gateway:
        async def generate_structured(self, **kwargs: Any) -> StructuredResult[Any]:
            prompts.append(kwargs["prompt"])
            return StructuredResult(
                data=PageCleanup(corrected_text="merged", legibility_score=0.8),
                usage=None,  # type: ignore[arg-type]
                response_id=None,
                model_version="test",
            )

    def ocr(image: bytes) -> str:
        return "scan words" if image else ""

    document = NormalizedDocument(
        filename="mixed.pdf",
        media_type="application/pdf",
        pages=(
            NormalizedPage(number=1, image_png=b"one", embedded_text="embedded words"),
            NormalizedPage(number=2, image_png=b"two", embedded_text=None),
        ),
    )

    await OCRProcessor(gateway=Gateway(), tesseract_runner=ocr).process(document)

    assert "embedded words" in prompts[0] and "scan words" in prompts[0]
    assert "NO_EMBEDDED_TEXT" in prompts[1] and "scan words" in prompts[1]
