"""Paths, constants, and configuration for the validation harness."""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = REPO_ROOT / "data" / "synthetic"
GROUND_TRUTH_DIR = DATA_ROOT / "ground_truth"
DISTRICT_DIR = DATA_ROOT / "district"
PROGRESS_DIR = DATA_ROOT / "progress"
DOCUMENTS_DIR = DATA_ROOT / "documents"
EXPECTED_DIR = Path(__file__).resolve().parent / "expected"

API_BASE_URL = os.environ.get("HARNESS_API_URL", "http://localhost:8000")
RATE_LIMIT_SECONDS = float(os.environ.get("HARNESS_RATE_LIMIT", "4.0"))

REFERENCE_DATE = date(2026, 11, 13)
SCHOOL_YEAR = "2026-2027"

SILENT_WRONG_THRESHOLD = 0.85

GEMINI_FLASH_COST_PER_1K_INPUT_TOKENS = 0.00001875
GEMINI_FLASH_COST_PER_1K_OUTPUT_TOKENS = 0.000075
ESTIMATED_TOKENS_PER_PAGE = 1500
ESTIMATED_OUTPUT_TOKENS_PER_DOC = 2000
