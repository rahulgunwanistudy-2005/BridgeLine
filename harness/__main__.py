"""CLI entry point: python -m harness {rules|extraction|acceptance|all}."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from harness import reporter


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="harness",
        description="BridgeLine validation harness — run evaluation suites.",
    )
    parser.add_argument(
        "suite",
        choices=["rules", "extraction", "acceptance", "all"],
        help="Which suite to run.",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed mismatch information.",
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="Skip RESULTS.md generation.",
    )
    args = parser.parse_args()

    rules_result = None
    acceptance_result = None
    extraction_result = None
    exit_code = 0

    if args.suite in ("rules", "all"):
        from harness.suites.rules import run as run_rules

        rules_result = run_rules(verbose=args.verbose)
        if not rules_result.passed:
            exit_code = 1

    if args.suite in ("acceptance", "all"):
        from harness.suites.acceptance import run as run_acceptance

        acceptance_result = run_acceptance(verbose=args.verbose)
        if not acceptance_result.passed:
            exit_code = 1

    if args.suite in ("extraction", "all"):
        from harness.suites.extraction import run as run_extraction

        extraction_result = run_extraction(verbose=args.verbose)
        if not extraction_result.passed and extraction_result.server_available:
            exit_code = 1

    if not args.no_report:
        results_path = Path(__file__).resolve().parent / "RESULTS.md"
        reporter.generate(
            rules_result=rules_result,
            acceptance_result=acceptance_result,
            extraction_result=extraction_result,
            output_path=results_path,
        )
        print(f"Results written to {results_path}")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
