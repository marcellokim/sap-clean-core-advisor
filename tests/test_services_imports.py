"""Tests for lightweight package import behavior."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest


class ServicesImportTests(unittest.TestCase):
    def test_importing_config_utils_does_not_load_heavy_services_stack(self) -> None:
        code = """
import json
import sys
import services.config_utils  # noqa: F401
print(json.dumps({
    "analysis_service_loaded": "services.analysis_service" in sys.modules,
    "gemini_provider_loaded": "services.infrastructure.llm.gemini_provider" in sys.modules,
    "streamlit_loaded": "streamlit" in sys.modules,
}))
"""
        output = subprocess.check_output([sys.executable, "-c", code], text=True)
        state = json.loads(output.strip())
        self.assertFalse(state["analysis_service_loaded"])
        self.assertFalse(state["gemini_provider_loaded"])
        self.assertFalse(state["streamlit_loaded"])


if __name__ == "__main__":
    unittest.main()

