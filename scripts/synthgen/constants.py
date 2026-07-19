"""Fixed constants that make the whole dataset deterministic and reproducible.

Nothing here may read the wall clock or the environment. Every date, seed, and
identifier is pinned so that regenerating the dataset produces byte-identical output.
"""

from __future__ import annotations

import uuid
from datetime import date
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMAS_DIR = REPO_ROOT / "packages" / "schemas"
DATA_DIR = REPO_ROOT / "data" / "synthetic"
DISTRICT_DIR = DATA_DIR / "district"
GROUND_TRUTH_DIR = DATA_DIR / "ground_truth"
PROGRESS_DIR = DATA_DIR / "progress"
GRADEBOOK_DIR = PROGRESS_DIR / "gradebook"
SERVICE_LOG_DIR = PROGRESS_DIR / "service_logs"
TEACHER_NOTES_DIR = PROGRESS_DIR / "teacher_notes"
DOCUMENTS_DIR = DATA_DIR / "documents"
PDF_DIR = DOCUMENTS_DIR / "pdf"
MESSY_DIR = DOCUMENTS_DIR / "messy"
ASSETS_DIR = DATA_DIR / "assets"

# ── Determinism ──────────────────────────────────────────────────────────────
# Single fixed seed for every random perturbation (variant generation, degradation).
RANDOM_SEED = 20260719

# Namespace for uuid5-derived stable identifiers. Fixed forever; changing it would
# renumber every record and break reconciliation lineage.
UUID_NAMESPACE = uuid.UUID("b8f2c1a4-5e6d-4f9a-8b2c-1d3e5f7a9c0b")

# Dataset epoch: the single timestamp stamped into extraction_meta.extracted_at for
# every hand-authored record. Fixed (never datetime.now()) so output is byte-stable.
DATASET_EPOCH_ISO = "2026-07-19T00:00:00Z"

# The model identifier recorded on hand-authored ground truth. These records are
# authored, not model-extracted, and the value states that honestly.
GROUND_TRUTH_MODEL = "ground-truth/hand-authored-v1"

# ── District facts ───────────────────────────────────────────────────────────
DISTRICT_NAME = "Riverside Demo School District"
SCHOOL_NAME = "Riverside Demo High School"
SCHOOL_YEAR = "2026-2027"

# Fall 2026 semester bounds and the fixed demo reference date ("now"). The dashboard
# and deadline rules evaluate against AS_OF, not the wall clock, so the demo and the
# harness are reproducible on any day.
SEMESTER_FIRST_DAY = date(2026, 8, 17)
SEMESTER_LAST_DAY = date(2026, 12, 18)
AS_OF = date(2026, 11, 13)


def stable_uuid(*parts: str) -> str:
    """Deterministic UUID from stable string parts via uuid5 on the fixed namespace."""

    key = "/".join(parts)
    return str(uuid.uuid5(UUID_NAMESPACE, key))
