"""Integration-style tests for analysis service orchestration."""

from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch

from models.schemas import CustomerInput, ModuleInfo
from services.analysis_service import AnalysisPolicy, analyze_customer_input, analyze_customer_input_cached
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
        self._old_disable_cache = os.environ.get("DISABLE_CACHE")
        settings.RULESET_GENERATED_DIR = self._tmp_dir.name
        settings.RULESET_ALLOW_GENERATED = False
        settings.ANALYSIS_MODE = "hybrid"
        os.environ["DISABLE_CACHE"] = "1"
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
        if self._old_disable_cache is None:
            os.environ.pop("DISABLE_CACHE", None)
        else:
            os.environ["DISABLE_CACHE"] = self._old_disable_cache
        resolve_ruleset_profile.cache_clear()
        self._tmp_dir.cleanup()

    @patch("services.application.analysis_runner.FPDFRenderer.render", return_value=b"%PDF-test")
    @patch("services.application.analysis_runner.GeminiLLMProvider.__init__", return_value=None)
    @patch("services.application.analysis_runner.ChromaRAGProvider.__init__", return_value=None)
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
        _mock_rag_init: object,
        _mock_llm_init: object,
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

    def test_disable_cache_bypasses_cached_wrapper(self) -> None:
        customer_input = _sample_input()
        expected_result = object()
        env_policy = AnalysisPolicy(
            analysis_mode="hybrid",
            rag_enabled=True,
            llm_enabled=True,
            timeout_ms=321,
        )

        with patch("services.analysis_service.AnalysisPolicy.from_env", return_value=env_policy) as mock_from_env:
            with patch("services.analysis_service.analyze_customer_input_cached") as mock_cached:
                with patch("services.analysis_service.run_analysis", return_value=expected_result) as mock_run_analysis:
                    result = analyze_customer_input(customer_input, lang="en")

        self.assertIs(result, expected_result)
        mock_from_env.assert_called_once_with()
        mock_cached.assert_not_called()
        mock_run_analysis.assert_called_once_with(customer_input, policy=env_policy, lang="en")

    def test_cache_enabled_serializes_input_and_policy_for_cached_wrapper(self) -> None:
        customer_input = _sample_input()
        expected_result = object()
        env_policy = AnalysisPolicy(
            analysis_mode="hybrid",
            rag_enabled=False,
            llm_enabled=True,
            timeout_ms=123,
        )
        os.environ.pop("DISABLE_CACHE", None)

        with patch("services.analysis_service.AnalysisPolicy.from_env", return_value=env_policy) as mock_from_env:
            with patch("services.analysis_service.analyze_customer_input_cached", return_value=expected_result) as mock_cached:
                result = analyze_customer_input(customer_input, lang="en")

        self.assertIs(result, expected_result)
        mock_from_env.assert_called_once_with()
        mock_cached.assert_called_once_with(
            customer_input.model_dump(),
            lang="en",
            policy_dict={
                "analysis_mode": "hybrid",
                "rag_enabled": False,
                "llm_enabled": True,
                "timeout_ms": 123,
            },
        )

    def test_cached_wrapper_rehydrates_customer_input_and_policy(self) -> None:
        expected_result = object()
        customer_input_dict = _sample_input().model_dump()
        policy_dict = {
            "analysis_mode": "hybrid",
            "rag_enabled": False,
            "llm_enabled": True,
            "timeout_ms": 99,
        }

        with patch("services.analysis_service.run_analysis", return_value=expected_result) as mock_run_analysis:
            result = analyze_customer_input_cached(customer_input_dict, lang="en", policy_dict=policy_dict)

        self.assertIs(result, expected_result)
        called_customer_input = mock_run_analysis.call_args.args[0]
        self.assertIsInstance(called_customer_input, CustomerInput)
        self.assertEqual(called_customer_input.company_name, customer_input_dict["company_name"])
        self.assertEqual(called_customer_input.modules[0].module_name, "FI")
        self.assertEqual(
            mock_run_analysis.call_args.kwargs["policy"],
            AnalysisPolicy(
                analysis_mode="hybrid",
                rag_enabled=False,
                llm_enabled=True,
                timeout_ms=99,
            ),
        )
        self.assertEqual(mock_run_analysis.call_args.kwargs["lang"], "en")

    def test_cached_wrapper_uses_env_policy_when_policy_dict_missing(self) -> None:
        expected_result = object()
        env_policy = AnalysisPolicy(
            analysis_mode="llm_only",
            rag_enabled=True,
            llm_enabled=True,
            timeout_ms=77,
        )

        with patch("services.analysis_service.AnalysisPolicy.from_env", return_value=env_policy) as mock_from_env:
            with patch("services.analysis_service.run_analysis", return_value=expected_result) as mock_run_analysis:
                result = analyze_customer_input_cached(_sample_input().model_dump(), lang="en")

        self.assertIs(result, expected_result)
        mock_from_env.assert_called_once_with()
        self.assertEqual(mock_run_analysis.call_args.kwargs["policy"], env_policy)
        self.assertEqual(mock_run_analysis.call_args.kwargs["lang"], "en")

    @patch("services.application.analysis_runner.FPDFRenderer.render", return_value=b"%PDF-test")
    @patch("services.application.analysis_runner.GeminiLLMProvider.__init__", return_value=None)
    @patch("services.application.analysis_runner.ChromaRAGProvider.__init__", return_value=None)
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
    @patch.object(settings, "ANALYSIS_MODE", "llm_only")
    def test_llm_mode_when_provider_succeeds(
        self,
        _mock_llm: object,
        _mock_rag: object,
        _mock_rag_init: object,
        _mock_llm_init: object,
        _mock_pdf: object,
    ) -> None:
        result = analyze_customer_input(_sample_input())
        self.assertEqual(result.output.generation_mode, "llm")
        self.assertIsNone(result.output.generation_error_code)
        self.assertEqual(result.output.executive_summary, "LLM EXEC")
        self.assertEqual(result.output.detailed_report, "LLM DETAIL")
        self.assertTrue(result.output.evidence_ledger)
        self.assertIn("llm_ms", result.output.stage_metrics_ms)
    @patch("services.application.analysis_runner.FPDFRenderer.render", return_value=b"%PDF-test")
    @patch("services.application.analysis_runner.GeminiLLMProvider.__init__", return_value=None)
    @patch("services.application.analysis_runner.ChromaRAGProvider.__init__", return_value=None)
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
        _mock_rag_init: object,
        _mock_llm_init: object,
        _mock_pdf: object,
    ) -> None:
        result = analyze_customer_input(_sample_input(industry="UnknownVertical"))
        self.assertEqual(result.output.ruleset_profile_source, "base")
        self.assertTrue(
            any("INDUSTRY_MAPPING_FALLBACK_TO_BASE" in w for w in result.output.validation_warnings)
        )


if __name__ == "__main__":
    unittest.main()
