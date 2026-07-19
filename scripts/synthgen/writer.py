"""Deterministic file writers so regeneration is byte-stable.

JSON is serialized with a fixed indent, ASCII escaping, stable key order (insertion
order, which the builders control), and a single trailing newline. No timestamps, no
randomness, nothing that varies between runs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, indent=2, ensure_ascii=True, sort_keys=False)
    path.write_text(text + "\n", encoding="utf-8")


def write_csv(path: Path, columns: list[str], rows: list[dict[str, Any]],
              extra_raw_lines: list[str] | None = None) -> None:
    """Write rows as CSV with '\\n' terminators; optionally append raw (malformed) lines."""

    import csv
    import io

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns, lineterminator="\n",
                            extrasaction="raise")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    text = buffer.getvalue()
    if extra_raw_lines:
        text += "\n".join(extra_raw_lines) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
