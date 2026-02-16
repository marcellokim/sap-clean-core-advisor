"""Integration-style tests for analysis service orchestration."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from models.schemas import CustomerInput, ModuleInfo
from services.analysis_service import analyze_customer_input
from services.error_codes import ERR_LLM_RATE_LIMIT
from services.llm_provider import LLMProviderError, ReportSections
from services.rag_pipeline import RAGContextBundle


def _sample_input(industry: str = "제조") -> CustomerInput:
    return CustomerInput(
        company_name="테스트제조",
        industry=industry,
        erp_version="ECC 6.0",
        db_type="Oracle",
        db_size_gb=500.0,
        num_users=800,
        num_custom_programs=350,
        custom_code_ratio=45.0,
        modules=[
            ModuleInfo(module_name="FI", customization_level="medium"),
            ModuleInfo(module_name="CO", customization_level="medium"),
            ModuleInfo(module_name="MM", customization_level="medium"),
            ModuleInfo(module_name="SD", customization_level="medium"),
        ],
        annual_it_budget_krw=50.0,
        pain_points="결산 지연",
        migration_timeline_months=18,
    )


class AnalysisServiceTests(unittest.TestCase):
    @patch("services.analysis_service.generate_pdf", return_value=b"%PDF-test")
    @patch(
        "services.analysis_service.get_context_bundle_for_input",
        return_value=RAGContextBundle(
            context="[출처: x]\n테스트 컨텍스트",
            sources=["x"],
            chunk_count=1,
        ),
    )
    @patch(
        "services.llm_engine.GeminiReportProvider.generate_report",
        side_effect=LLMProviderError(ERR_LLM_RATE_LIMIT, "429"),
    )
    def test_fallback_mode_on_rate_limit(
        self,
        _mock_llm: object,
        _mock_rag: object,
        _mock_pdf: object,
    ) -> None:
        result = analyze_customer_input(_sample_input())
        self.assertEqual(result.output.generation_mode, "fallback")
        self.assertEqual(result.output.generation_error_code, ERR_LLM_RATE_LIMIT)
        self.assertEqual(result.output.generation_provider, "gemini")
        self.assertTrue(result.output.ruleset_version)
        self.assertEqual(result.output.ruleset_profile_source, "industry")
        self.assertEqual(result.output.ruleset_profile_id, "manufacturing")
        self.assertTrue(result.output.evidence_ledger)
        self.assertIn("calc_ms", result.output.stage_metrics_ms)
        self.assertIn("total_ms", result.output.stage_metrics_ms)
        self.assertTrue(result.output.executive_summary)
        self.assertIsNotNone(result.pdf_bytes)

    @patch("services.analysis_service.generate_pdf", return_value=b"%PDF-test")
    @patch(
        "services.analysis_service.get_context_bundle_for_input",
        return_value=RAGContextBundle(
            context="[출처: x]\n테스트 컨텍스트",
            sources=["x"],
            chunk_count=1,
        ),
    )
    @patch(
        "services.llm_engine.GeminiReportProvider.generate_report",
        return_value=ReportSections(
            executive_summary="LLM EXEC",
            detailed_report="LLM DETAIL",
        ),
    )
    def test_llm_mode_when_provider_succeeds(
        self,
        _mock_llm: object,
        _mock_rag: object,
        _mock_pdf: object,
    ) -> None:
        result = analyze_customer_input(_sample_input())
        self.assertEqual(result.output.generation_mode, "llm")
        self.assertIsNone(result.output.generation_error_code)
        self.assertEqual(result.output.executive_summary, "LLM EXEC")
        self.assertEqual(result.output.detailed_report, "LLM DETAIL")
        self.assertTrue(result.output.evidence_ledger)
        self.assertIn("llm_ms", result.output.stage_metrics_ms)

    @patch("services.analysis_service.generate_pdf", return_value=b"%PDF-test")
    @patch(
        "services.analysis_service.get_context_bundle_for_input",
        return_value=RAGContextBundle(
            context="",
            sources=[],
            chunk_count=0,
        ),
    )
    @patch(
        "services.llm_engine.GeminiReportProvider.generate_report",
        side_effect=LLMProviderError(ERR_LLM_RATE_LIMIT, "429"),
    )
    def test_unknown_industry_uses_base_profile_and_warning(
        self,
        _mock_llm: object,
        _mock_rag: object,
        _mock_pdf: object,
    ) -> None:
        result = analyze_customer_input(_sample_input(industry="UnknownVertical"))
        self.assertEqual(result.output.ruleset_profile_source, "base")
        self.assertTrue(
            any("INDUSTRY_MAPPING_FALLBACK_TO_BASE" in w for w in result.output.validation_warnings)
        )


if __name__ == "__main__":
    unittest.main()
