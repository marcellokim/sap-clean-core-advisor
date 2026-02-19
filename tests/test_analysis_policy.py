"""Tests for policy-driven analysis mode behavior."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from models.schemas import CustomerInput, ModuleInfo
from services.application.analysis_runner import AnalysisPolicy, run_analysis
from services.llm_provider import ReportSections
from services.rag_pipeline import RAGContextBundle


def _sample_input() -> CustomerInput:
    return CustomerInput(
        company_name="테스트제조",
        industry="제조",
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


class AnalysisPolicyTests(unittest.TestCase):
    @patch("services.application.analysis_runner.FPDFRenderer.render", return_value=b"%PDF-test")
    @patch("services.application.analysis_runner.GeminiLLMProvider.generate_report")
    @patch("services.application.analysis_runner.ChromaRAGProvider.get_context_bundle")
    def test_deterministic_mode_skips_rag_and_llm(
        self,
        mock_rag: object,
        mock_llm: object,
        _mock_pdf: object,
    ) -> None:
        result = run_analysis(
            _sample_input(),
            policy=AnalysisPolicy(analysis_mode="deterministic", rag_enabled=True, llm_enabled=True),
        )
        self.assertEqual(result.output.analysis_mode, "deterministic")
        self.assertEqual(result.output.rag_status, "skipped")
        self.assertEqual(result.output.llm_status, "skipped")
        self.assertEqual(result.output.generation_mode, "fallback")
        self.assertEqual(result.output.pdf_status, "ok")
        mock_rag.assert_not_called()
        mock_llm.assert_not_called()

    @patch("services.application.analysis_runner.FPDFRenderer.render", return_value=b"%PDF-test")
    @patch(
        "services.application.analysis_runner.GeminiLLMProvider.generate_report",
        return_value=ReportSections(executive_summary="LLM EXEC", detailed_report="LLM DETAIL"),
    )
    @patch(
        "services.application.analysis_runner.ChromaRAGProvider.get_context_bundle",
        return_value=RAGContextBundle(context="[출처: x]\nctx", sources=["x"], chunk_count=1),
    )
    def test_hybrid_mode_runs_rag_and_llm(
        self,
        mock_rag: object,
        mock_llm: object,
        _mock_pdf: object,
    ) -> None:
        result = run_analysis(
            _sample_input(),
            policy=AnalysisPolicy(analysis_mode="hybrid", rag_enabled=True, llm_enabled=True),
        )
        self.assertEqual(result.output.analysis_mode, "hybrid")
        self.assertEqual(result.output.rag_status, "ok")
        self.assertEqual(result.output.llm_status, "ok")
        self.assertEqual(result.output.generation_mode, "llm")
        self.assertEqual(result.output.pdf_status, "ok")
        mock_rag.assert_called_once()
        mock_llm.assert_called_once()


if __name__ == "__main__":
    unittest.main()

