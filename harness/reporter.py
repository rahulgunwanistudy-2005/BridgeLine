"""Auto-generate RESULTS.md from suite results."""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from harness.suites.acceptance import AcceptanceSuiteResult
    from harness.suites.extraction import ExtractionSuiteResult
    from harness.suites.rules import RulesSuiteResult


def _git_commit_hash() -> str:
    """Get the current git commit short hash."""

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        return result.stdout.strip() or "unknown"
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"


def generate(
    *,
    rules_result: RulesSuiteResult | None = None,
    acceptance_result: AcceptanceSuiteResult | None = None,
    extraction_result: ExtractionSuiteResult | None = None,
    output_path: Path | None = None,
) -> str:
    """Generate RESULTS.md content from suite results."""

    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    commit = _git_commit_hash()
    lines: list[str] = []

    lines.append("# Validation Harness — Results\n")
    lines.append(f"> Generated: {now}  ")
    lines.append(f"> Commit: `{commit}`\n")

    # Summary table
    lines.append("## Summary\n")
    lines.append("| Suite | Status | Duration |")
    lines.append("|-------|--------|----------|")

    if rules_result:
        status = "✅ PASS" if rules_result.passed else "❌ FAIL"
        lines.append(
            f"| Rules (Slice 1) | {status} "
            f"({rules_result.passed_records}/{rules_result.total_records}) "
            f"| {rules_result.elapsed_seconds:.2f}s |"
        )

    if acceptance_result:
        status = "✅ PASS" if acceptance_result.passed else "❌ FAIL"
        lines.append(
            f"| Acceptance (Slice 3) | {status} "
            f"({acceptance_result.passed_findings}/{acceptance_result.total_findings}) "
            f"| {acceptance_result.elapsed_seconds:.2f}s |"
        )

    if extraction_result:
        if not extraction_result.server_available:
            status = "⚠️ SKIPPED"
        elif extraction_result.passed:
            status = "✅ PASS"
        else:
            status = "❌ FAIL"
        lines.append(
            f"| Extraction (Slice 2) | {status} "
            f"| {extraction_result.elapsed_seconds:.1f}s |"
        )

    lines.append("")

    # Rules suite detail
    if rules_result:
        rules_version = ""
        for r in rules_result.records:
            expected_path = Path(__file__).parent / "expected" / f"{r.student_ref}.obligations.json"
            if expected_path.exists():
                import json

                data = json.loads(expected_path.read_text())
                rules_version = data.get("rules_version", "")
                break

        lines.append("## Slice 1 — Rules Derivation\n")
        if rules_version:
            lines.append(f"Rules engine version: `{rules_version}`\n")
        lines.append(f"Determinism hash: `{rules_result.determinism_hash[:16]}`\n")

        lines.append("| Student | Obligations | Findings | Deadlines | Deterministic | Status |")
        lines.append("|---------|-------------|----------|-----------|---------------|--------|")

        for r in rules_result.records:
            det = "✅" if r.deterministic else "❌"
            obl = f"{r.actual_obligations}/{r.expected_obligations}"
            find = f"{r.actual_findings}/{r.expected_findings}"
            dead = f"{r.actual_deadlines}/{r.expected_deadlines}"
            ok = r.obligation_match and r.finding_match and r.deterministic
            status = "✅" if ok else "❌"
            lines.append(f"| {r.student_ref} | {obl} | {find} | {dead} | {det} | {status} |")

            if r.error:
                lines.append(f"| | ERROR: {r.error} | | | | |")

        lines.append("")

        if any(r.mismatches for r in rules_result.records):
            lines.append("### Mismatches\n")
            for r in rules_result.records:
                if r.mismatches:
                    lines.append(f"**{r.student_ref}**:")
                    for m in r.mismatches[:5]:
                        lines.append(f"- {m}")
                    if len(r.mismatches) > 5:
                        lines.append(f"- ... and {len(r.mismatches) - 5} more")
                    lines.append("")

    # Acceptance suite detail
    if acceptance_result:
        lines.append("## Slice 3 — E2E Acceptance\n")
        lines.append("| Finding | Status | Detail |")
        lines.append("|---------|--------|--------|")

        for f in acceptance_result.findings:
            status = "✅" if f.passed else "❌"
            detail = f.actual[:100] if f.actual else ""
            lines.append(f"| {f.name} | {status} | {detail} |")

        lines.append("")

    # Extraction suite detail
    if extraction_result:
        lines.append("## Slice 2 — Extraction Pipeline\n")

        if not extraction_result.server_available:
            lines.append(
                "> ⚠️ API server was not available. Results below are a dry-run inventory.\n"
            )

        tiers = extraction_result.by_tier
        for tier_name in ["clean", "degraded", "scan"]:
            docs = tiers.get(tier_name, [])
            if not docs:
                continue

            processed = [d for d in docs if d.error is None]
            total_fields = sum(d.total_fields for d in processed)
            correct = sum(d.correct_fields for d in processed)
            accuracy = correct / total_fields if total_fields > 0 else 0.0

            lines.append(f"### {tier_name.title()} tier ({len(docs)} documents)\n")
            if processed:
                lines.append(f"- Field accuracy: **{accuracy:.1%}** ({correct}/{total_fields})")
            else:
                lines.append(f"- Documents: {len(docs)} (not processed)")
            lines.append("")

        # Silent-wrong-rate
        lines.append("### Silent-wrong-rate\n")
        if extraction_result.server_available:
            swr = extraction_result.silent_wrong_rate
            lines.append(
                f"**{swr:.1%}** — fields where value ≠ ground truth "
                f"AND confidence ≥ {0.85:.0%}\n"
            )
        else:
            lines.append("Not computed (server unavailable)\n")

        # Failure examples
        examples = extraction_result.top_failure_examples
        if examples:
            lines.append("### Failure examples\n")
            lines.append("| Student | Field | Expected | Got | Confidence |")
            lines.append("|---------|-------|----------|-----|------------|")
            for ex in examples:
                lines.append(
                    f"| {ex['student_ref']} | {ex['field']} "
                    f"| {ex['expected']} | {ex['actual']} "
                    f"| {ex['confidence']:.2f} |"
                )
            lines.append("")

        # Cost
        lines.append(f"Estimated cost: **${extraction_result.estimated_cost_usd:.2f}** USD\n")

    # Residual variance disclosure
    lines.append("---\n")
    lines.append("## Disclosures\n")
    lines.append(
        "- **Rules engine** (Slices 1, 3): fully deterministic, zero LLM calls "
        "(AST-enforced boundary). Repeated runs produce byte-identical output.\n"
    )
    lines.append(
        "- **Extraction pipeline** (Slice 2): uses Gemini for OCR and extraction. "
        "Results carry residual LLM variance; the silent-wrong-rate is the safety metric.\n"
    )

    content = "\n".join(lines) + "\n"

    if output_path:
        output_path.write_text(content, encoding="utf-8")

    return content
