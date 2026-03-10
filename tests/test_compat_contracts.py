"""Compatibility contract tests for wrapper/adaptor entrypoints."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

import services
from models.schemas import AdvisorOutput, CustomerInput, ModuleInfo
from services.analysis_service import AnalysisPolicy, AnalysisResult, analyze_customer_input
from services.infrastructure.pdf import FPDFRenderer
from services.infrastructure.rag import ChromaRAGProvider
from services.rag_pipeline import RAGContextBundle


def _sample_customer_input() -> CustomerInput:
    return CustomerInput(
        company_name="Compat Corp",
        industry="제조",
        erp_version="ECC 6.0",
        db_type="Oracle",
        db_size_gb=250.0,
        num_users=200,
        num_custom_programs=80,
        custom_code_ratio=20.0,
        modules=[ModuleInfo(module_name="FI", customization_level="medium")],
        annual_it_budget_krw=10.0,
        pain_points="결산 지연",
        migration_timeline_months=12,
    )


def _sample_output() -> AdvisorOutput:
    return AdvisorOutput(
        clean_core_score=42.6,
        score_breakdown={
            "custom_code": 32.5,
            "erp_version": 40.0,
            "database": 45.0,
            "module_complexity": 58.0,
        },
        current_annual_tco=1.06,
        projected_tco_after_migration=0.95,
        tco_savings_3yr=0.33,
        risk_level="Medium",
        risk_factors=["custom code"],
        recommendations=["retire Z-code"],
        executive_summary="summary",
        detailed_report="detail",
        tech_debt_breakdown={"FI": 40.5},
        generation_mode="fallback",
        analysis_id="compat-analysis",
    )


def _sample_analysis_result() -> AnalysisResult:
    return AnalysisResult(
        output=_sample_output(),
        pdf_bytes=b"%PDF-compat",
        pdf_error_code=None,
        pdf_error_message=None,
    )


class AnalysisServiceContractTests(unittest.TestCase):
    def test_service_module_reexports_runner_contract(self) -> None:
        from services.application.analysis_runner import AnalysisPolicy as RunnerPolicy
        from services.application.analysis_runner import AnalysisResult as RunnerResult
        from services.application.analysis_runner import run_analysis as runner_run_analysis

        self.assertIs(services.AnalysisPolicy, RunnerPolicy)
        self.assertIs(services.AnalysisResult, RunnerResult)
        self.assertIs(services.run_analysis, runner_run_analysis)

    def test_analyze_customer_input_uses_env_policy_when_not_provided(self) -> None:
        customer = _sample_customer_input()
        expected = _sample_analysis_result()
        env_policy = AnalysisPolicy(analysis_mode="hybrid", rag_enabled=True, llm_enabled=True, timeout_ms=321)
        previous_disable_cache = os.environ.get("DISABLE_CACHE")
        os.environ["DISABLE_CACHE"] = "1"
        try:
            with patch("services.analysis_service.AnalysisPolicy.from_env", return_value=env_policy) as mock_from_env:
                with patch("services.analysis_service.run_analysis", return_value=expected) as mock_run_analysis:
                    result = analyze_customer_input(customer, lang="en")
        finally:
            if previous_disable_cache is None:
                os.environ.pop("DISABLE_CACHE", None)
            else:
                os.environ["DISABLE_CACHE"] = previous_disable_cache

        self.assertIs(result, expected)
        mock_from_env.assert_called_once_with()
        mock_run_analysis.assert_called_once_with(customer, policy=env_policy, lang="en")

    def test_analyze_customer_input_preserves_explicit_policy(self) -> None:
        customer = _sample_customer_input()
        expected = _sample_analysis_result()
        policy = AnalysisPolicy(analysis_mode="deterministic", rag_enabled=False, llm_enabled=False, timeout_ms=0)
        previous_disable_cache = os.environ.get("DISABLE_CACHE")
        os.environ["DISABLE_CACHE"] = "1"
        try:
            with patch("services.analysis_service.AnalysisPolicy.from_env") as mock_from_env:
                with patch("services.analysis_service.run_analysis", return_value=expected) as mock_run_analysis:
                    result = analyze_customer_input(customer, lang="ko", policy=policy)
        finally:
            if previous_disable_cache is None:
                os.environ.pop("DISABLE_CACHE", None)
            else:
                os.environ["DISABLE_CACHE"] = previous_disable_cache

        self.assertIs(result, expected)
        mock_from_env.assert_not_called()
        mock_run_analysis.assert_called_once_with(customer, policy=policy, lang="ko")


class FPDFRendererContractTests(unittest.TestCase):
    def test_render_returns_generate_pdf_bytes_without_shape_changes(self) -> None:
        customer = _sample_customer_input()
        output = _sample_output()
        renderer = FPDFRenderer()

        with patch("services.infrastructure.pdf.fpdf_renderer.generate_pdf", return_value=b"%PDF-contract") as mock_generate_pdf:
            result = renderer.render(output, customer)

        self.assertEqual(result, b"%PDF-contract")
        mock_generate_pdf.assert_called_once_with(output, customer)

    def test_render_propagates_generate_pdf_exceptions(self) -> None:
        customer = _sample_customer_input()
        output = _sample_output()
        renderer = FPDFRenderer()

        with patch("services.infrastructure.pdf.fpdf_renderer.generate_pdf", side_effect=RuntimeError("font missing")):
            with self.assertRaisesRegex(RuntimeError, "font missing"):
                renderer.render(output, customer)


class ChromaProviderContractTests(unittest.TestCase):
    def test_init_warms_cached_vector_store(self) -> None:
        with patch("services.infrastructure.rag.chroma_provider.get_cached_vector_store") as mock_get_cached_vector_store:
            provider = ChromaRAGProvider()

        self.assertIsInstance(provider, ChromaRAGProvider)
        mock_get_cached_vector_store.assert_called_once_with()

    def test_get_context_bundle_delegates_to_rag_pipeline(self) -> None:
        bundle = RAGContextBundle(context="ctx", sources=["src"], chunk_count=1)
        with patch("services.infrastructure.rag.chroma_provider.get_cached_vector_store"):
            provider = ChromaRAGProvider()

        with patch(
            "services.infrastructure.rag.chroma_provider.get_context_bundle_for_input",
            return_value=bundle,
        ) as mock_get_context_bundle:
            result = provider.get_context_bundle(
                erp_version="ECC 6.0",
                modules=["FI", "CO"],
                pain_points="closing",
            )

        self.assertEqual(result, bundle)
        mock_get_context_bundle.assert_called_once_with(
            erp_version="ECC 6.0",
            modules=["FI", "CO"],
            pain_points="closing",
        )


if __name__ == "__main__":
    unittest.main()
