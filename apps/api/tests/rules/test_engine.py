"""Rule driver determinism and structural safety tests."""

import ast
import hashlib
from pathlib import Path

from bridgeline.rules import engine as engine_module
from bridgeline.rules.engine import derive_obligations
from bridgeline.rules.types import ApprovedRecord, RosterSnapshot


def test_identical_inputs_are_byte_identical(
    approved_record: ApprovedRecord, roster: RosterSnapshot
) -> None:
    first = derive_obligations(approved_record, roster).model_dump_json()
    second = derive_obligations(approved_record, roster).model_dump_json()

    assert first == second
    assert hashlib.sha256(first.encode()).digest() == hashlib.sha256(second.encode()).digest()


def test_rules_package_has_no_llm_or_provider_imports() -> None:
    assert engine_module.__file__ is not None
    package = Path(engine_module.__file__).parent
    forbidden = ("bridgeline.llm", "openai", "google.genai", "google.generativeai")

    for path in package.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        modules = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        modules.update(
            node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
        )
        assert not any(
            module == prefix or module.startswith(f"{prefix}.")
            for module in modules
            for prefix in forbidden
        ), f"forbidden import in {path}"
