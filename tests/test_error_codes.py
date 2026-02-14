"""Tests for centralized error code taxonomy."""

from __future__ import annotations

import unittest

from services import error_codes as ec


class ErrorCodeTests(unittest.TestCase):
    def test_all_error_codes_use_err_prefix_and_are_unique(self) -> None:
        codes = [
            ec.ERR_LLM_DISABLED,
            ec.ERR_LLM_RATE_LIMIT,
            ec.ERR_LLM_AUTH,
            ec.ERR_LLM_PROVIDER,
            ec.ERR_PROVIDER_NOT_SUPPORTED,
            ec.ERR_RAG_UNAVAILABLE,
            ec.ERR_PDF_LAYOUT_OVERFLOW,
            ec.ERR_PDF_FONT,
            ec.ERR_PDF_UNKNOWN,
        ]
        self.assertEqual(len(codes), len(set(codes)))
        self.assertTrue(all(code.startswith("ERR_") for code in codes))


if __name__ == "__main__":
    unittest.main()
