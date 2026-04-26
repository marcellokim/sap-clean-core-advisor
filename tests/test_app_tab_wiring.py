"""Tests for app tab wiring split and UI behavior."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from models.schemas import AdvisorOutput, CustomerInput, GapAnalysisOutput, ModuleInfo
from services.application.analysis_runner import AnalysisPolicy, AnalysisResult
from ui.tabs import clean_core, joule


class _DummyStatus:
    def __init__(self) -> None:
        self.updates: list[dict[str, object]] = []

    def __enter__(self) -> "_DummyStatus":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
        return False

    def update(self, **kwargs: object) -> None:
        self.updates.append(kwargs)


class _DummyColumn:
    def __enter__(self) -> "_DummyColumn":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
        return False


def _sample_input() -> CustomerInput:
    return CustomerInput(
        company_name="테스트 제조",
        industry="제조",
        erp_version="ECC 6.0",
        db_type="Oracle",
        db_size_gb=120.0,
        num_users=500,
        num_custom_programs=150,
        custom_code_ratio=25.0,
        modules=[ModuleInfo(module_name="FI", customization_level="medium")],
        annual_it_budget_krw=12.0,
        pain_points="수동 결산",
        migration_timeline_months=18,
    )


def _sample_output() -> AdvisorOutput:
    return AdvisorOutput(
        clean_core_score=72.0,
        score_breakdown={
            "custom_code": 70.0,
            "erp_version": 75.0,
            "database": 68.0,
            "module_complexity": 76.0,
        },
        current_annual_tco=15.0,
        projected_tco_after_migration=11.0,
        tco_savings_3yr=12.0,
        risk_level="Medium",
        risk_factors=["커스텀 비중 높음"],
        recommendations=["코드 정리"],
        executive_summary="요약",
        detailed_report="상세",
        tech_debt_breakdown={"FI": 30.0},
        generation_mode="fallback",
        generation_provider="gemini",
        generation_error_code=None,
        analysis_id="analysis-1",
        analysis_mode="hybrid",
        rag_status="ok",
        llm_status="fallback",
        pdf_status="ok",
        ruleset_version="2026.03",
        ruleset_profile_id="manufacturing",
        ruleset_profile_source="industry",
        calibration_quality={},
        llm_usage_source="none",
        llm_usage_tokens={},
        llm_cost_estimate_usd=0.0,
        llm_monthly_projection_usd={},
        validation_warnings=[],
        stage_metrics_ms={
            "calc_ms": 1,
            "rag_ms": 1,
            "llm_ms": 1,
            "pdf_ms": 1,
            "total_ms": 4,
        },
        evidence_ledger=[],
    )


class AppTabWiringTests(unittest.TestCase):
    def test_clean_core_empty_state_localizes_for_ko_and_en(self) -> None:
        for ui_lang, expected_title, expected_snippet in (
            (
                "KO",
                "분석 준비",
                "상단 폼에 고객사 정보를 입력하면 Clean Core score, 기술 부채, TCO 비교, EA Cookbook 초안을 한 번에 생성합니다.",
            ),
            (
                "EN",
                "Prepare the assessment",
                "Complete the intake form above to generate the Clean Core score, technical debt view, TCO comparison, and a draft EA Cookbook in one pass.",
            ),
        ):
            with self.subTest(ui_lang=ui_lang):
                session_state: dict[str, object] = {"ui_lang": ui_lang}

                with (
                    patch.object(clean_core, "render_input_form", return_value=None),
                    patch.object(clean_core.st, "session_state", session_state, create=True),
                    patch.object(clean_core, "render_empty_state_panel") as mock_panel,
                ):
                    clean_core.render_clean_core_tab()

                mock_panel.assert_called_once()
                self.assertEqual(mock_panel.call_args.kwargs["title"], expected_title)
                self.assertIn(expected_snippet, mock_panel.call_args.kwargs["description"])
                self.assertGreater(len(mock_panel.call_args.kwargs["highlights"]), 0)

    def test_clean_core_success_stores_session_state_and_renders_dashboard(self) -> None:
        customer_input = _sample_input()
        output = _sample_output()
        analysis_result = AnalysisResult(
            output=output,
            pdf_bytes=b"%PDF-test",
            pdf_error_code=None,
            pdf_error_message=None,
        )
        session_state: dict[str, object] = {"ui_lang": "KO"}
        status = _DummyStatus()

        with (
            patch.object(clean_core, "render_input_form", return_value=customer_input),
            patch.object(clean_core, "get_locked_analysis_policy", return_value=AnalysisPolicy(analysis_mode="hybrid")),
            patch.object(clean_core, "analyze_customer_input", return_value=analysis_result),
            patch.object(clean_core, "render_dashboard") as mock_dashboard,
            patch.object(clean_core.st, "session_state", session_state, create=True),
            patch.object(clean_core.st, "status", return_value=status),
            patch.object(clean_core.st, "write"),
            patch.object(clean_core.st, "warning"),
            patch.object(clean_core.st, "caption"),
        ):
            clean_core.render_clean_core_tab()

        self.assertIs(session_state["last_output"], output)
        self.assertEqual(session_state["last_input"], customer_input)
        self.assertEqual(session_state["last_pdf"], b"%PDF-test")
        mock_dashboard.assert_called_once_with(output, customer_input, b"%PDF-test")
        self.assertEqual(status.updates[-1]["state"], "complete")

    def test_clean_core_loading_message_and_analysis_lang_follow_ui_language(self) -> None:
        customer_input = _sample_input()
        output = _sample_output()
        analysis_result = AnalysisResult(
            output=output,
            pdf_bytes=b"%PDF-test",
            pdf_error_code=None,
            pdf_error_message=None,
        )

        for ui_lang, expected_status, expected_lang in (
            (
                "KO",
                "AI가 SAP Clean Core 분석을 수행하고 있습니다. 캐시된 결과가 없다면 약 30~60초가 소요됩니다.",
                "ko",
            ),
            (
                "EN",
                "AI is running the SAP Clean Core analysis. Expect roughly 30 to 60 seconds when no cached result is available.",
                "en",
            ),
        ):
            with self.subTest(ui_lang=ui_lang):
                session_state: dict[str, object] = {"ui_lang": ui_lang}
                status = _DummyStatus()
                policy = AnalysisPolicy(analysis_mode="hybrid")

                with (
                    patch.object(clean_core, "render_input_form", return_value=customer_input),
                    patch.object(clean_core, "get_locked_analysis_policy", return_value=policy),
                    patch.object(clean_core, "analyze_customer_input", return_value=analysis_result) as mock_analyze,
                    patch.object(clean_core, "render_dashboard"),
                    patch.object(clean_core.st, "session_state", session_state, create=True),
                    patch.object(clean_core.st, "status", return_value=status) as mock_status,
                    patch.object(clean_core.st, "write"),
                    patch.object(clean_core.st, "warning"),
                    patch.object(clean_core.st, "caption"),
                ):
                    clean_core.render_clean_core_tab()

                mock_status.assert_called_once_with(expected_status, expanded=True)
                mock_analyze.assert_called_once_with(customer_input, lang=expected_lang, policy=policy)
                self.assertEqual(status.updates[-1]["state"], "complete")

    def test_clean_core_exception_shows_error_and_caption(self) -> None:
        customer_input = _sample_input()
        session_state: dict[str, object] = {"ui_lang": "KO"}
        status = _DummyStatus()

        with (
            patch.object(clean_core, "render_input_form", return_value=customer_input),
            patch.object(clean_core, "get_locked_analysis_policy", return_value=AnalysisPolicy(analysis_mode="hybrid")),
            patch.object(clean_core, "analyze_customer_input", side_effect=RuntimeError("rate limit")),
            patch.object(clean_core.st, "session_state", session_state, create=True),
            patch.object(clean_core.st, "status", return_value=status),
            patch.object(clean_core.st, "write"),
            patch.object(clean_core.st, "error") as mock_error,
            patch.object(clean_core.st, "caption") as mock_caption,
            patch.object(clean_core.settings, "LLM_PROVIDER", "gemini"),
            patch.object(clean_core.settings, "GOOGLE_API_KEY", "configured"),
        ):
            clean_core.render_clean_core_tab()

        mock_error.assert_called_once()
        mock_caption.assert_called_once()
        self.assertEqual(status.updates[-1]["state"], "error")
        self.assertNotIn("last_output", session_state)

    def test_clean_core_missing_api_key_localizes_error_without_caption(self) -> None:
        customer_input = _sample_input()

        for ui_lang, expected_message in (
            (
                "KO",
                "분석 중 오류가 발생했습니다. 선택한 LLM provider API 키가 .env 파일에 설정되어 있는지 확인하세요.",
            ),
            (
                "EN",
                "An error occurred during analysis. Check that the selected LLM provider API key is configured in the .env file.",
            ),
        ):
            with self.subTest(ui_lang=ui_lang):
                session_state: dict[str, object] = {"ui_lang": ui_lang}
                status = _DummyStatus()

                with (
                    patch.object(clean_core, "render_input_form", return_value=customer_input),
                    patch.object(clean_core, "get_locked_analysis_policy", return_value=AnalysisPolicy(analysis_mode="hybrid")),
                    patch.object(clean_core, "analyze_customer_input", side_effect=RuntimeError("auth failed")),
                    patch.object(clean_core.st, "session_state", session_state, create=True),
                    patch.object(clean_core.st, "status", return_value=status),
                    patch.object(clean_core.st, "write"),
                    patch.object(clean_core.st, "error") as mock_error,
                    patch.object(clean_core.st, "caption") as mock_caption,
                    patch.object(clean_core.settings, "LLM_PROVIDER", "gemini"),
                    patch.object(clean_core.settings, "GOOGLE_API_KEY", ""),
                ):
                    clean_core.render_clean_core_tab()

                mock_error.assert_called_once_with(expected_message)
                mock_caption.assert_not_called()
                self.assertEqual(status.updates[-1]["state"], "error")

    def test_joule_tab_callback_wires_module_handler(self) -> None:
        callback_holder: dict[str, object] = {}
        status = _DummyStatus()
        result = GapAnalysisOutput(
            identified_gaps=["권한 준비 부족"],
            recommended_actions=["권한 매핑 수립"],
            risk_level="High",
            executive_summary="즉시 조치 필요",
        )

        with (
            patch.object(joule, "render_joule_checklist", side_effect=lambda cb: callback_holder.setdefault("callback", cb)),
            patch.object(joule, "generate_joule_gap_analysis", return_value=result) as mock_generate,
            patch.object(joule.st, "session_state", {"ui_lang": "KO"}, create=True),
            patch.object(joule.st, "status", return_value=status),
            patch.object(joule.st, "write"),
            patch.object(joule.st, "markdown"),
            patch.object(joule.st, "subheader"),
            patch.object(joule.st, "caption"),
            patch.object(joule.st, "container", return_value=_DummyColumn()),
            patch.object(joule.st, "columns", return_value=(_DummyColumn(), _DummyColumn())),
            patch.object(joule, "render_section_heading"),
        ):
            joule.render_joule_tab()
            callback = callback_holder["callback"]
            self.assertIs(callback, joule.handle_gap_analysis)
            callback(["checked"], ["unchecked"])

        mock_generate.assert_called_once_with(["checked"], ["unchecked"])
        self.assertEqual(status.updates[-1]["state"], "complete")

    def test_app_entrypoint_has_no_inline_tab_handlers(self) -> None:
        source = Path("app.py").read_text(encoding="utf-8")
        self.assertNotIn("def _render_clean_core_tab", source)
        self.assertNotIn("def _handle_gap_analysis", source)


if __name__ == "__main__":
    unittest.main()
