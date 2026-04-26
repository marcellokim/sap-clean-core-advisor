"""Tests for LLM runtime timeout handling."""

from __future__ import annotations

import unittest

from services.application.llm_runtime import generate_with_optional_timeout
from services.llm_provider import ReportPayload, ReportSections


def _payload() -> ReportPayload:
    return ReportPayload(
        analysis_date="2026-04-26",
        customer_info="customer",
        clean_core_score=70.0,
        score_breakdown={},
        current_tco=1.0,
        projected_tco=0.8,
        savings_3yr=0.6,
        risk_level="Medium",
        risk_factors=[],
        tech_debt={},
        recommendations=[],
        rag_context="",
    )


class _CountingProvider:
    provider_name = "test"

    def __init__(self) -> None:
        self.calls = 0

    def generate_report(self, payload: ReportPayload) -> ReportSections:
        self.calls += 1
        return ReportSections(executive_summary="summary", detailed_report="detail")


class LLMRuntimeTests(unittest.TestCase):
    def test_exhausted_timeout_budget_does_not_start_provider_call(self) -> None:
        provider = _CountingProvider()

        with self.assertRaises(TimeoutError):
            generate_with_optional_timeout(provider, _payload(), lambda: 0.0)

        self.assertEqual(provider.calls, 0)

    def test_none_timeout_runs_provider_inline(self) -> None:
        provider = _CountingProvider()

        result = generate_with_optional_timeout(provider, _payload(), lambda: None)

        self.assertEqual(result.executive_summary, "summary")
        self.assertEqual(provider.calls, 1)


if __name__ == "__main__":
    unittest.main()
