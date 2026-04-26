"""Tests for Gemini infrastructure adapter configuration."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from services.infrastructure.llm.gemini_provider import GeminiLLMProvider


class GeminiProviderTests(unittest.TestCase):
    @patch("services.infrastructure.llm.gemini_provider.ChatGoogleGenerativeAI")
    def test_provider_passes_http_timeout_to_client(self, mock_chat: object) -> None:
        with patch.multiple(
            "config.settings.settings",
            GOOGLE_API_KEY="test-key",
            GEMINI_MODEL="gemini-test",
            LLM_HTTP_TIMEOUT_SEC=9,
        ):
            GeminiLLMProvider()

        self.assertEqual(mock_chat.call_args.kwargs["request_timeout"], 9)


if __name__ == "__main__":
    unittest.main()
