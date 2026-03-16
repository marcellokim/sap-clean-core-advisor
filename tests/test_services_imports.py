"""Tests for lightweight package import behavior."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest


def _probe_import_state(code: str) -> dict[str, bool]:
    output = subprocess.check_output([sys.executable, "-c", code], text=True)
    return json.loads(output.strip())


class ServicesImportTests(unittest.TestCase):
    def test_importing_config_utils_does_not_load_heavy_services_stack(self) -> None:
        state = _probe_import_state(
            """
import json
import sys
import services.config_utils  # noqa: F401
print(json.dumps({
    "analysis_service_loaded": "services.analysis_service" in sys.modules,
    "gemini_provider_loaded": "services.infrastructure.llm.gemini_provider" in sys.modules,
    "streamlit_loaded": "streamlit" in sys.modules,
}))
"""
        )
        self.assertFalse(state["analysis_service_loaded"])
        self.assertFalse(state["gemini_provider_loaded"])
        self.assertFalse(state["streamlit_loaded"])

    def test_importing_services_package_does_not_load_heavy_services_stack(self) -> None:
        state = _probe_import_state(
            """
import json
import sys
import services  # noqa: F401
print(json.dumps({
    "analysis_service_loaded": "services.analysis_service" in sys.modules,
    "streamlit_loaded": "streamlit" in sys.modules,
    "heavy_loaded": any(
        name.startswith(("chromadb", "langchain", "sentence_transformers"))
        for name in sys.modules
    ),
}))
"""
        )
        self.assertFalse(state["analysis_service_loaded"])
        self.assertFalse(state["streamlit_loaded"])
        self.assertFalse(state["heavy_loaded"])

    def test_importing_ruleset_export_does_not_load_heavy_services_stack(self) -> None:
        state = _probe_import_state(
            """
import json
import sys
from services import resolve_ruleset_profile  # noqa: F401
print(json.dumps({
    "analysis_service_loaded": "services.analysis_service" in sys.modules,
    "streamlit_loaded": "streamlit" in sys.modules,
    "heavy_loaded": any(
        name.startswith(("chromadb", "langchain", "sentence_transformers"))
        for name in sys.modules
    ),
}))
"""
        )
        self.assertFalse(state["analysis_service_loaded"])
        self.assertFalse(state["streamlit_loaded"])
        self.assertFalse(state["heavy_loaded"])


if __name__ == "__main__":
    unittest.main()
