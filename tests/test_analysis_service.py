"""Integration-style tests for analysis service orchestration."""

from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch

from models.schemas import CustomerInput, ModuleInfo
from services.analysis_service import analyze_customer_input
from services.error_codes import ERR_LLM_RATE_LIMIT
from services.llm_provider import LLMProviderError, ReportSections
from services.rag_pipeline import RAGContextBundle
from services.ruleset_loader import resolve_ruleset_profile
from config.settings import settings


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
    def setUp(self) -> None:
        self._tmp_dir = tempfile.TemporaryDirectory()
        self._old_generated = settings.RULESET_GENERATED_DIR
        self._old_generated_flag = settings.RULESET_ALLOW_GENERATED
        self._old_mode = settings.ANALYSIS_MODE
        settings.RULESET_GENERATED_DIR = self._tmp_dir.name
        settings.RULESET_ALLOW_GENERATED = False
        settings.ANALYSIS_MODE = "hybrid"
        resolve_ruleset_profile.cache_clear()

    def tearDown(self) -> None:
        if self._old_generated is None:
            settings.RULESET_GENERATED_DIR = ""
        else:
            settings.RULESET_GENERATED_DIR = self._old_generated
        if self._old_generated_flag is None:
            settings.RULESET_ALLOW_GENERATED = False
        else:
            settings.RULESET_ALLOW_GENERATED = self._old_generated_flag
        if self._old_mode is None:
            settings.ANALYSIS_MODE = "deterministic"
        else:
            settings.ANALYSIS_MODE = self._old_mode
        resolve_ruleset_profile.cache_clear()
        self._tmp_dir.cleanup()

    @patch("services.application.analysis_runner.FPDFRenderer.render", return_value=b"%PDF-test")
    @patch(
        "services.application.analysis_runner.ChromaRAGProvider.get_context_bundle",
        return_value=RAGContextBundle(
            context="[출처: x]\n테스트 컨텍스트",
            sources=["x"],
            chunk_count=1,
        ),
    )
    @patch(
        "services.application.analysis_runner.GeminiLLMProvider.generate_report",
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
        self.assertEqual(result.output.llm_usage_source, "estimated")
        self.assertGreater(result.output.llm_usage_tokens.get("total_tokens", 0), 0)
        self.assertGreaterEqual(result.output.llm_cost_estimate_usd, 0.0)
        self.assertIn("1000_runs", result.output.llm_monthly_projection_usd)
        self.assertIsNotNone(result.pdf_bytes)

    @patch("services.application.analysis_runner.FPDFRenderer.render", return_value=b"%PDF-test")
    @patch(
        "services.application.analysis_runner.ChromaRAGProvider.get_context_bundle",
        return_value=RAGContextBundle(
            context="[출처: x]\n테스트 컨텍스트",
            sources=["x"],
            chunk_count=1,
        ),
    )
    @patch(
        "services.application.analysis_runner.GeminiLLMProvider.generate_report",
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
        self.assertGreater(result.output.llm_usage_tokens.get("total_tokens", 0), 0)
        self.assertGreaterEqual(result.output.llm_cost_estimate_usd, 0.0)

    @patch("services.application.analysis_runner.FPDFRenderer.render", return_value=b"%PDF-test")
    @patch(
        "services.application.analysis_runner.ChromaRAGProvider.get_context_bundle",
        return_value=RAGContextBundle(
            context="",
            sources=[],
            chunk_count=0,
        ),
    )
    @patch(
        "services.application.analysis_runner.GeminiLLMProvider.generate_report",
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
