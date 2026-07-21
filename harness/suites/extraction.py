"""Slice 2 — LLM extraction pipeline evaluation suite.

Uploads documents to the ingest API, compares extracted IEPRecords against
ground truth, and reports per-tier accuracy and the silent-wrong-rate.

Requires a running API server at HARNESS_API_URL (default: localhost:8000).
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from urllib.error import URLError
from urllib.request import Request, urlopen

from harness.config import (
    API_BASE_URL,
    DOCUMENTS_DIR,
    ESTIMATED_OUTPUT_TOKENS_PER_DOC,
    ESTIMATED_TOKENS_PER_PAGE,
    GEMINI_FLASH_COST_PER_1K_INPUT_TOKENS,
    GEMINI_FLASH_COST_PER_1K_OUTPUT_TOKENS,
    GROUND_TRUTH_DIR,
    RATE_LIMIT_SECONDS,
    SILENT_WRONG_THRESHOLD,
)


@dataclass
class DocumentResult:
    """Result from one document extraction comparison."""

    filename: str
    tier: str
    student_ref: str | None = None
    total_fields: int = 0
    correct_fields: int = 0
    silent_wrong_fields: int = 0
    error: str | None = None
    failure_examples: list[dict] = field(default_factory=list)


@dataclass
class ExtractionSuiteResult:
    """Aggregate result for the extraction suite."""

    documents: list[DocumentResult] = field(default_factory=list)
    elapsed_seconds: float = 0.0
    estimated_cost_usd: float = 0.0
    server_available: bool = False
    passed: bool = False

    @property
    def total_documents(self) -> int:
        return len(self.documents)

    @property
    def by_tier(self) -> dict[str, list[DocumentResult]]:
        tiers: dict[str, list[DocumentResult]] = {}
        for d in self.documents:
            tiers.setdefault(d.tier, []).append(d)
        return tiers

    @property
    def silent_wrong_rate(self) -> float:
        total = sum(d.total_fields for d in self.documents if d.error is None)
        silent = sum(d.silent_wrong_fields for d in self.documents if d.error is None)
        return silent / total if total > 0 else 0.0

    @property
    def top_failure_examples(self) -> list[dict]:
        examples = []
        for d in self.documents:
            examples.extend(d.failure_examples)
        return examples[:3]


def _classify_tier(filename: str) -> str:
    """Classify a document into clean / degraded / scan."""

    if filename.startswith("scan"):
        return "scan"
    parts = filename.replace(".pdf", "").split("-")
    if len(parts) >= 2 and parts[0] == "RIV":
        ref_num = int(parts[1])
        if 1001 <= ref_num <= 1012:
            return "clean"
    return "degraded"


def _check_server() -> bool:
    """Check if the API server is reachable."""

    try:
        req = Request(f"{API_BASE_URL}/docs", method="HEAD")
        urlopen(req, timeout=5)
        return True
    except (URLError, OSError):
        return False


def _compare_fields(
    ground_truth: dict, extracted: dict, student_ref: str
) -> tuple[int, int, int, list[dict]]:
    """Compare extracted fields against ground truth.

    Returns: (total, correct, silent_wrong, failure_examples)
    """

    fields_to_check = [
        "student_ref",
        "disability_category",
        "school_year",
    ]
    date_fields = ["annual_review", "triennial_reeval", "last_progress_report"]

    total = 0
    correct = 0
    silent_wrong = 0
    failures: list[dict] = []

    for field_name in fields_to_check:
        total += 1
        expected = ground_truth.get(field_name)
        actual = extracted.get(field_name)
        confidence = (
            extracted.get("field_confidences", {}).get(field_name, 0.0)
            if "field_confidences" in extracted
            else 0.0
        )

        if actual == expected:
            correct += 1
        elif confidence >= SILENT_WRONG_THRESHOLD:
            silent_wrong += 1
            failures.append({
                "student_ref": student_ref,
                "field": field_name,
                "expected": str(expected),
                "actual": str(actual),
                "confidence": confidence,
            })

    gt_dates = ground_truth.get("dates", {})
    ex_dates = extracted.get("dates", {})
    for field_name in date_fields:
        total += 1
        expected = gt_dates.get(field_name)
        actual = ex_dates.get(field_name)
        confidence = (
            extracted.get("field_confidences", {}).get(field_name, 0.0)
            if "field_confidences" in extracted
            else 0.0
        )

        if actual == expected:
            correct += 1
        elif confidence >= SILENT_WRONG_THRESHOLD:
            silent_wrong += 1
            failures.append({
                "student_ref": student_ref,
                "field": field_name,
                "expected": str(expected),
                "actual": str(actual),
                "confidence": confidence,
            })

    # Compare accommodation count
    total += 1
    gt_accom = len(ground_truth.get("accommodations", []))
    ex_accom = len(extracted.get("accommodations", []))
    if gt_accom == ex_accom:
        correct += 1

    # Compare service count
    total += 1
    gt_svc = len(ground_truth.get("services", []))
    ex_svc = len(extracted.get("services", []))
    if gt_svc == ex_svc:
        correct += 1

    # Compare goal count
    total += 1
    gt_goals = len(ground_truth.get("goals", []))
    ex_goals = len(extracted.get("goals", []))
    if gt_goals == ex_goals:
        correct += 1

    return total, correct, silent_wrong, failures


def _estimate_cost(documents: list[DocumentResult]) -> float:
    """Estimate the USD cost of a full extraction run."""

    total_pages = sum(4 for _ in documents)  # Each IEP is 4 pages
    input_tokens = total_pages * ESTIMATED_TOKENS_PER_PAGE
    output_tokens = len(documents) * ESTIMATED_OUTPUT_TOKENS_PER_DOC
    input_cost = (input_tokens / 1000) * GEMINI_FLASH_COST_PER_1K_INPUT_TOKENS
    output_cost = (output_tokens / 1000) * GEMINI_FLASH_COST_PER_1K_OUTPUT_TOKENS
    return input_cost + output_cost


def run(*, verbose: bool = False) -> ExtractionSuiteResult:
    """Run the extraction pipeline evaluation."""

    suite = ExtractionSuiteResult()
    start = time.monotonic()

    print(f"\n{'='*60}")
    print("  EXTRACTION SUITE — document pipeline evaluation")
    print(f"{'='*60}\n")

    # Check server
    suite.server_available = _check_server()
    if not suite.server_available:
        print(f"  ⚠ API server not available at {API_BASE_URL}")
        print("  Set HARNESS_API_URL or start the server to run this suite.")
        print("  Generating a dry-run estimate instead.\n")

        # Enumerate documents for cost estimate
        pdf_dir = DOCUMENTS_DIR / "pdf"
        scan_dir = DOCUMENTS_DIR / "scans"
        if pdf_dir.exists():
            for pdf in sorted(pdf_dir.glob("*.pdf")):
                tier = _classify_tier(pdf.name)
                suite.documents.append(
                    DocumentResult(filename=pdf.name, tier=tier, error="server_unavailable")
                )
        if scan_dir.exists():
            for scan in sorted(scan_dir.glob("*.pdf")):
                suite.documents.append(
                    DocumentResult(filename=scan.name, tier="scan", error="server_unavailable")
                )

        suite.estimated_cost_usd = _estimate_cost(suite.documents)
        suite.elapsed_seconds = time.monotonic() - start

        print(f"  Documents enumerated: {suite.total_documents}")
        tiers = suite.by_tier
        for tier, docs in sorted(tiers.items()):
            print(f"    {tier}: {len(docs)}")
        print(f"  Estimated cost: ${suite.estimated_cost_usd:.2f}")
        print("\n  Extraction Suite: ⚠ SKIPPED (server unavailable)\n")
        return suite

    # If server is available, run the actual pipeline
    pdf_dir = DOCUMENTS_DIR / "pdf"
    if not pdf_dir.exists():
        print("  ✗ No PDF directory found at data/synthetic/documents/pdf/")
        suite.elapsed_seconds = time.monotonic() - start
        return suite

    pdfs = sorted(pdf_dir.glob("*.pdf"))
    print(f"  Processing {len(pdfs)} documents...\n")

    for i, pdf_path in enumerate(pdfs):
        tier = _classify_tier(pdf_path.name)
        dr = DocumentResult(filename=pdf_path.name, tier=tier)

        try:
            # Upload the document
            boundary = "----HarnessFormBoundary"
            body = (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="file"; filename="{pdf_path.name}"\r\n'
                f"Content-Type: application/pdf\r\n\r\n"
            ).encode() + pdf_path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()

            req = Request(
                f"{API_BASE_URL}/ieps/upload",
                data=body,
                headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
                method="POST",
            )
            with urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read())

            dr.student_ref = result.get("student_ref")

            # Load ground truth if available
            gt_ref = pdf_path.stem.split(".")[0]
            gt_path = GROUND_TRUTH_DIR / f"{gt_ref}.iep.json"
            if gt_path.exists():
                gt = json.loads(gt_path.read_text(encoding="utf-8"))
                total, correct, silent, failures = _compare_fields(
                    gt, result, gt_ref
                )
                dr.total_fields = total
                dr.correct_fields = correct
                dr.silent_wrong_fields = silent
                dr.failure_examples = failures
            else:
                dr.error = "no_ground_truth"

        except (URLError, OSError) as exc:
            dr.error = str(exc)

        suite.documents.append(dr)

        status = "✓" if dr.error is None else "✗"
        accuracy = (
            f"{dr.correct_fields}/{dr.total_fields}"
            if dr.total_fields > 0
            else "n/a"
        )
        print(f"  {status} [{tier:8s}] {pdf_path.name}: {accuracy}")

        if i < len(pdfs) - 1:
            time.sleep(RATE_LIMIT_SECONDS)

    suite.estimated_cost_usd = _estimate_cost(suite.documents)
    suite.elapsed_seconds = time.monotonic() - start

    # Summary
    processed = [d for d in suite.documents if d.error is None]
    total_fields = sum(d.total_fields for d in processed)
    correct_fields = sum(d.correct_fields for d in processed)
    accuracy = correct_fields / total_fields if total_fields > 0 else 0.0

    print(f"\n  Processed: {len(processed)}/{suite.total_documents}")
    print(f"  Field accuracy: {accuracy:.1%} ({correct_fields}/{total_fields})")
    print(f"  Silent-wrong-rate: {suite.silent_wrong_rate:.1%}")
    print(f"  Estimated cost: ${suite.estimated_cost_usd:.2f}")
    print(f"  Elapsed: {suite.elapsed_seconds:.1f}s")

    suite.passed = suite.silent_wrong_rate == 0.0
    result_emoji = "✓ PASS" if suite.passed else "✗ FAIL"
    print(f"\n  Extraction Suite: {result_emoji}\n")
    return suite
