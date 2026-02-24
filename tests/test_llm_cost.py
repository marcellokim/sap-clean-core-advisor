"""Tests for LLM usage normalization and cost estimator."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from services.llm_cost import (
    build_monthly_projection,
    estimate_cost_usd,
    normalize_usage_metadata,
)
from services.llm_provider import LLMUsage


class LlmCostTests(unittest.TestCase):
    def test_normalize_usage_metadata_supports_provider_keys(self) -> None:
        usage = normalize_usage_metadata(
            {
                "input_tokens": 1234,
                "output_tokens": 456,
                "total_tokens": 1690,
            }
        )
        self.assertEqual(usage.prompt_tokens, 1234)
        self.assertEqual(usage.output_tokens, 456)
        self.assertEqual(usage.total_tokens, 1690)
        self.assertEqual(usage.source, "provider")

    def test_estimate_cost_usd_applies_token_prices(self) -> None:
        usage = LLMUsage(prompt_tokens=3000, output_tokens=1000, total_tokens=4000, source="estimated")
        with patch.multiple(
            "config.settings.settings",
            LLM_PRICE_INPUT_PER_1M=0.075,
            LLM_PRICE_OUTPUT_PER_1M=0.30,
        ):
            cost = estimate_cost_usd(usage)
        self.assertAlmostEqual(cost, 0.000525, places=9)

    def test_monthly_projection_includes_env_target(self) -> None:
        with patch.multiple("config.settings.settings", LLM_MONTHLY_REQUESTS=2500):
            projection = build_monthly_projection(0.001)
        self.assertIn("100_runs", projection)
        self.assertIn("1000_runs", projection)
        self.assertIn("2500_runs", projection)
        self.assertAlmostEqual(projection["2500_runs"], 2.5, places=6)


if __name__ == "__main__":
    unittest.main()

