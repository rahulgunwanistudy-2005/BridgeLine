#!/usr/bin/env python
"""Idempotently seed the Riverside synthetic dataset via the public API.

Territory rule: seeding goes through the API, never direct DB writes. The required
endpoints are PROPOSED (see docs/seed-api-contract.md) and not yet implemented, so this
loader is **gated**: it waits for the API, probes each endpoint, and cleanly no-ops
(exit 0) on 404 so `docker compose up` never fails on first boot. Set SEED_STRICT=1 to
make missing endpoints a hard error once the backend lands.

Stdlib only (urllib) so it runs in any minimal Python image without dependencies.

Env:
  BRIDGELINE_API_URL   base URL (default http://localhost:8000)
  SEED_TOKEN           value sent as X-Seed-Token (default "")
  SEED_STRICT          "1" to fail on missing/failing endpoints (default off)
  SEED_MAX_WAIT_SECONDS wait budget for /health (default 60)
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA = REPO_ROOT / "data" / "synthetic"

API_URL = os.environ.get("BRIDGELINE_API_URL", "http://localhost:8000").rstrip("/")
SEED_TOKEN = os.environ.get("SEED_TOKEN", "")
STRICT = os.environ.get("SEED_STRICT") == "1"
MAX_WAIT = float(os.environ.get("SEED_MAX_WAIT_SECONDS", "60"))


class SeedGatedError(RuntimeError):
    """A required endpoint is not implemented yet (404) while SEED_STRICT is on."""


def _log(msg: str) -> None:
    print(f"[seed] {msg}", flush=True)


def _request(method: str, path: str, body: object | None = None) -> tuple[int, bytes]:
    url = f"{API_URL}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if SEED_TOKEN:
        req.add_header("X-Seed-Token", SEED_TOKEN)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()
    except urllib.error.URLError as exc:
        raise ConnectionError(f"{method} {path}: {exc.reason}") from exc


def wait_for_health() -> bool:
    deadline = time.monotonic() + MAX_WAIT
    while time.monotonic() < deadline:
        try:
            status, _ = _request("GET", "/health")
            if status == 200:
                _log(f"API healthy at {API_URL}")
                return True
        except ConnectionError:
            pass
        time.sleep(2)
    _log(f"API did not become healthy within {MAX_WAIT:.0f}s at {API_URL}")
    return False


def _load_json(rel: str) -> object:
    return json.loads((DATA / rel).read_text(encoding="utf-8"))


def _post_gated(path: str, body: object, label: str) -> bool:
    """POST an idempotent upsert; return True on success, False if gated (404)."""

    status, payload = _request("POST", path, body)
    if status == 404:
        _log(f"SKIP {label}: {path} not implemented yet (gated). See docs/seed-api-contract.md")
        if STRICT:
            raise SeedGatedError(path)
        return False
    if 200 <= status < 300:
        _log(f"OK   {label}: {path} -> {status}")
        return True
    detail = payload.decode(errors="replace")[:200]
    _log(f"FAIL {label}: {path} -> {status} {detail}")
    if STRICT:
        raise RuntimeError(f"{label} failed: {status} {detail}")
    return False


def seed_district() -> bool:
    district = _load_json("district/district.json")
    return _post_gated("/admin/seed/district", district, "district")


def seed_ieps() -> bool:
    gt_dir = DATA / "ground_truth"
    ok = True
    for iep_path in sorted(gt_dir.glob("*.iep.json")):
        record = json.loads(iep_path.read_text(encoding="utf-8"))
        # field_confidences is embedded in the record (schema v1.1); no sidecar to merge.
        body = {"record": record, "approve": True}
        ok = _post_gated("/ieps/import", body, f"iep {record['student_ref']}") and ok
        if not ok and not STRICT:
            # First 404 means the endpoint is absent; stop hammering it.
            break
    return ok


def seed_progress() -> bool:
    notes = _load_json("progress/teacher_notes/teacher_notes.json")
    body = {"source_name": "teacher_notes.json", "signal_type": "teacher_check_in", "rows": notes}
    return _post_gated("/reconcile/import", body, "teacher notes")


def main() -> int:
    _log(f"seeding from {DATA}")
    if not wait_for_health():
        return 1 if STRICT else 0
    try:
        results = [seed_district(), seed_ieps(), seed_progress()]
    except (SeedGatedError, RuntimeError) as exc:
        _log(f"strict failure: {exc}")
        return 1
    if not any(results):
        _log("no seed endpoints available yet — nothing loaded (gated no-op). "
             "This is expected until docs/seed-api-contract.md is implemented.")
    else:
        _log("seed complete (idempotent upserts).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
