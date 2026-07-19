"""Run the generated sample through Gemini-backed ingest stages without persistence."""

import asyncio
import json
from pathlib import Path
from uuid import uuid4

from bridgeline.config import get_settings
from bridgeline.ingest.extract import IEPExtractor
from bridgeline.ingest.gate import ConfidenceGate, reject_non_iep
from bridgeline.ingest.identity import reconcile_identities
from bridgeline.ingest.normalize import normalize_document
from bridgeline.ingest.ocr import OCRProcessor
from bridgeline.llm.client import GeminiGateway

SAMPLE = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "synthetic"
    / "fixtures"
    / "samples"
    / "clean-sample-iep.pdf"
)


async def main() -> None:
    """Print a non-sensitive, assertion-backed summary of the live smoke result."""

    settings = get_settings()
    gateway = GeminiGateway.from_settings(settings)
    document = await asyncio.to_thread(
        normalize_document,
        SAMPLE.read_bytes(),
        filename=SAMPLE.name,
        max_upload_bytes=settings.ingest_max_upload_bytes,
        pdf_dpi=settings.ingest_pdf_dpi,
    )
    print(f"normalized_pages={len(document.pages)}", flush=True)
    pages = await OCRProcessor(
        gateway=gateway,
        page_concurrency=settings.ingest_ocr_page_concurrency,
    ).process(document)
    print(f"cleaned_pages={len(pages)}", flush=True)
    extraction = await IEPExtractor(
        gateway=gateway,
        pages_per_chunk=settings.ingest_extraction_pages_per_chunk,
    ).extract(pages, iep_record_id=uuid4(), run_id=uuid4())
    print("structured_extraction=validated", flush=True)
    record = reconcile_identities(extraction.record, prior=None)
    classification = await reject_non_iep(
        pages,
        gateway=gateway,
        rejection_confidence=settings.ingest_non_iep_rejection_confidence,
    )
    print("classification=validated", flush=True)
    gate = ConfidenceGate(
        field_threshold=settings.ingest_field_confidence_threshold,
        legibility_threshold=settings.ingest_legibility_threshold,
    ).evaluate(record, classification)

    assert record.student_ref == "RIV-204"
    assert record.services[0].minutes_per_week == 150
    assert record.accommodations[0].source_page == 2
    assert record.goals[0].source_page == 3
    assert record.dates.annual_review is not None
    assert record.dates.triennial_reeval is not None
    assert record.dates.annual_review.isoformat() == "2027-05-10"
    assert record.dates.triennial_reeval.isoformat() == "2029-04-22"
    print(
        json.dumps(
            {
                "student_ref": record.student_ref,
                "page_count": record.extraction_meta.page_count,
                "legibility_scores": record.extraction_meta.legibility_scores,
                "accommodations": len(record.accommodations),
                "services": len(record.services),
                "goals": len(record.goals),
                "is_iep": classification.is_iep,
                "classification_confidence": classification.confidence,
                "gate_state": gate.state,
                "review_paths": [item.path for item in gate.review_fields],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
