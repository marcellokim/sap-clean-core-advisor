"""Regression tests for the default import budget path."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HEAVY_PREFIXES = ("chromadb", "langchain", "sentence_transformers")


def _snapshot_for(import_stmt: str) -> dict[str, object]:
    code = (
        "import json, sys\n"
        f"{import_stmt}\n"
        f"heavy_prefixes = {HEAVY_PREFIXES!r}\n"
        "mods = sorted(sys.modules)\n"
        "heavy = [name for name in mods if name.startswith(heavy_prefixes)]\n"
        "print(json.dumps({'module_count': len(mods), 'heavy_count': len(heavy), 'heavy_modules': heavy[:25]}))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout.strip())


class ImportBudgetTests(unittest.TestCase):
    def test_app_import_avoids_heavy_rag_and_llm_modules(self) -> None:
        snapshot = _snapshot_for("import app")
        self.assertEqual(snapshot["heavy_count"], 0, snapshot["heavy_modules"])

    def test_analysis_runner_import_avoids_heavy_rag_and_llm_modules(self) -> None:
        snapshot = _snapshot_for("from services.application.analysis_runner import run_analysis")
        self.assertEqual(snapshot["heavy_count"], 0, snapshot["heavy_modules"])


if __name__ == "__main__":
    unittest.main()
