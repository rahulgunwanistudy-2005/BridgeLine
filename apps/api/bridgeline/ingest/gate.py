"""Fail-closed document classification and confidence gating."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from bridgeline.db.schemas import IEPRecord, ReconciliationStatus
from bridgeline.ingest.ocr import OCRPage, StructuredGateway
from bridgeline.llm.prompts import PromptRegistry

__all__ = ["ConfidenceGate", "GateResult", "GateState", "ReviewField"]


class NonIEPDocumentError(ValueError):
    """Friendly rejection for a confidently classified non-IEP upload."""


class DocumentClassification(BaseModel):
    """Cheap typed IEP/non-IEP classification response."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    is_iep: bool
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = Field(min_length=1)


class GateState(StrEnum):
    """Outcome of deterministic confidence enforcement."""

    ACCEPTED = "accepted"
    NEEDS_REVIEW = "needs_review"


class ReviewField(BaseModel):
    """One explicit reason a path cannot be silently accepted."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    confidence: float | None
    reason: str


class GateResult(BaseModel):
    """Confidence gate outcome consumed by pipeline status and review UI."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    state: GateState
    review_fields: tuple[ReviewField, ...]


class ConfidenceGate:
    """Apply code thresholds to every available confidence source."""

    def __init__(
        self, *, field_threshold: float = 0.85, legibility_threshold: float = 0.70
    ) -> None:
        if not 0 <= field_threshold <= 1 or not 0 <= legibility_threshold <= 1:
            raise ValueError("confidence thresholds must be between zero and one")
        self._field_threshold = field_threshold
        self._legibility_threshold = legibility_threshold

    def evaluate(
        self,
        record: IEPRecord,
        classification: DocumentClassification | None = None,
    ) -> GateResult:
        """Flag low-confidence, low-legibility, and ambiguous-identity paths."""

        review: list[ReviewField] = []
        for index, score in enumerate(record.extraction_meta.legibility_scores):
            if score < self._legibility_threshold:
                review.append(
                    ReviewField(
                        path=f"extraction_meta.legibility_scores[{index}]",
                        confidence=score,
                        reason="Page legibility is below the configured threshold",
                    )
                )
        for collection_name in ("accommodations", "services", "goals"):
            items = getattr(record, collection_name)
            for index, item in enumerate(items):
                if item.confidence < self._field_threshold:
                    review.append(
                        ReviewField(
                            path=f"{collection_name}[{index}]",
                            confidence=item.confidence,
                            reason="Extraction confidence is below the configured threshold",
                        )
                    )
                if item.reconciliation_status is ReconciliationStatus.AMBIGUOUS:
                    review.append(
                        ReviewField(
                            path=f"{collection_name}[{index}].reconciliation_status",
                            confidence=None,
                            reason="Multiple prior identities are credible matches",
                        )
                    )
        for path, confidence in (
            ("student_ref", record.field_confidences.student_ref),
            ("disability_category", record.field_confidences.disability_category),
            ("school_year", record.field_confidences.school_year),
            ("dates.annual_review", record.field_confidences.annual_review),
            ("dates.triennial_reeval", record.field_confidences.triennial_reeval),
            ("dates.last_progress_report", record.field_confidences.last_progress_report),
        ):
            if confidence < self._field_threshold:
                review.append(
                    ReviewField(
                        path=path,
                        confidence=confidence,
                        reason="Field confidence is below the configured threshold",
                    )
                )
        if classification is not None and (
            not classification.is_iep or classification.confidence < self._field_threshold
        ):
            review.append(
                ReviewField(
                    path="document_classification",
                    confidence=classification.confidence,
                    reason="Document classification is uncertain and requires review",
                )
            )
        state = GateState.NEEDS_REVIEW if review else GateState.ACCEPTED
        return GateResult(state=state, review_fields=tuple(review))


async def reject_non_iep(
    pages: tuple[OCRPage, ...],
    *,
    gateway: StructuredGateway,
    rejection_confidence: float = 0.85,
    prompts: PromptRegistry | None = None,
) -> DocumentClassification:
    """Reject only a confidently classified non-IEP; uncertain cases continue to review."""

    registry = prompts or PromptRegistry()
    excerpt = "\n\n".join(
        f"PAGE {page.page_number}\n{page.corrected_text[:3000]}" for page in pages[:4]
    )
    prompt = registry.render("iep_classify", {"document_excerpt": excerpt})
    result = await gateway.generate_structured(
        prompt=prompt,
        response_model=DocumentClassification,
        max_output_tokens=512,
        temperature=0.0,
        thinking_level="minimal",
    )
    classification = result.data
    if not classification.is_iep and classification.confidence >= rejection_confidence:
        raise NonIEPDocumentError(
            "This document does not appear to be an IEP. Upload an approved or draft IEP document."
        )
    return classification
