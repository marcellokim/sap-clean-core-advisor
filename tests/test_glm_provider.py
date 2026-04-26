"""Tests for GLM infrastructure adapter behavior."""

from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from models.schemas import GapAnalysisOutput
from services.infrastructure.llm.glm_provider import GLMLLMProvider


class _FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
        return False

    def read(self) -> bytes:
        return json.dumps(self._payload, ensure_ascii=False).encode("utf-8")


class GLMProviderTests(unittest.TestCase):
    @patch("services.infrastructure.llm.glm_provider.request.urlopen")
    def test_generate_structured_output_validates_json_response(self, mock_urlopen: object) -> None:
        mock_urlopen.return_value = _FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": (
                                "```json\n"
                                "{\"identified_gaps\":[\"gap\"],"
                                "\"recommended_actions\":[\"act\"],"
                                "\"risk_level\":\"Low\","
                                "\"executive_summary\":\"summary\"}"
                                "\n```"
                            )
                        }
                    }
                ]
            }
        )

        with patch.multiple(
            "config.settings.settings",
            GLM_API_KEY="test-key",
            GLM_MODEL="glm-5",
            LLM_MODEL="",
            LLM_HTTP_TIMEOUT_SEC=7,
        ):
            provider = GLMLLMProvider()
            result = provider.generate_structured_output(
                system_prompt="system",
                user_prompt="user",
                output_model=GapAnalysisOutput,
            )

        self.assertEqual(result.identified_gaps, ["gap"])
        self.assertEqual(result.recommended_actions, ["act"])
        self.assertEqual(result.risk_level, "Low")
        self.assertEqual(mock_urlopen.call_args.kwargs["timeout"], 7)


if __name__ == "__main__":
    unittest.main()
