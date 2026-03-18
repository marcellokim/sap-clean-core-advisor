"""Regression tests for dashboard result-state rendering."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from models.schemas import AdvisorOutput, CustomerInput, ModuleInfo
from ui import dashboard


class _DummyContainer:
    def __enter__(self) -> "_DummyContainer":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
        return False


def _sample_input() -> CustomerInput:
    return CustomerInput(
        company_name="Global Manufacturing",
        industry="Manufacturing",
        erp_version="ECC 6.0",
        db_type="Oracle",
        db_size_gb=120.0,
        num_users=500,
        num_custom_programs=150,
        custom_code_ratio=25.0,
        modules=[
            ModuleInfo(module_name="FI", customization_level="medium"),
            ModuleInfo(module_name="MM", customization_level="low"),
        ],
        annual_it_budget_krw=12.0,
        pain_points="Manual close",
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
        risk_factors=["High custom-code share"],
        recommendations=["Retire obsolete Z-code"],
        executive_summary="Summary",
        detailed_report="Detailed report",
        tech_debt_breakdown={"FI": 30.0, "MM": 10.0},
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


class DashboardRegressionTests(unittest.TestCase):
    def test_render_dashboard_preserves_plotly_semantics_in_english_result_state(self) -> None:
        plotted: list[tuple[object, dict[str, object]]] = []

        def _columns(count: int | list[float]) -> tuple[_DummyContainer, ...]:
            if not isinstance(count, int):
                count = len(count)
            return tuple(_DummyContainer() for _ in range(count))

        with (
            patch.object(dashboard.st, "session_state", {"ui_lang": "EN"}, create=True),
            patch.object(dashboard.st, "markdown"),
            patch.object(dashboard.st, "success"),
            patch.object(dashboard.st, "info"),
            patch.object(dashboard.st, "metric"),
            patch.object(dashboard.st, "subheader"),
            patch.object(dashboard.st, "dataframe"),
            patch.object(dashboard.st, "caption"),
            patch.object(dashboard.st, "download_button"),
            patch.object(dashboard.st, "columns", side_effect=_columns),
            patch.object(dashboard.st, "plotly_chart", side_effect=lambda fig, **kwargs: plotted.append((fig, kwargs))),
            patch.object(dashboard.st, "expander", return_value=_DummyContainer()),
        ):
            dashboard.render_dashboard(_sample_output(), _sample_input(), b"%PDF-test")

        self.assertEqual(len(plotted), 4)
        self.assertTrue(all(kwargs["use_container_width"] is True for _, kwargs in plotted))

        gauge, breakdown, tech_debt, tco = [fig for fig, _ in plotted]

        self.assertEqual(gauge.data[0].type, "indicator")
        self.assertEqual(gauge.data[0].gauge["bar"]["color"], dashboard.SAP_GREEN)

        self.assertEqual(breakdown.data[0].type, "scatterpolar")
        self.assertEqual(
            list(breakdown.data[0].theta),
            ["Custom Code", "ERP Version", "Database", "Module Complexity", "Custom Code"],
        )
        self.assertEqual(breakdown.layout.title.text, "Score Breakdown Analysis")

        self.assertEqual(tech_debt.data[0].type, "bar")
        self.assertEqual(tech_debt.data[0].orientation, "h")
        self.assertEqual(list(tech_debt.data[0].y), ["FI", "MM"])

        self.assertEqual([trace.type for trace in tco.data], ["bar", "bar", "scatter"])
        self.assertEqual(
            [trace.name for trace in tco.data],
            ["Current TCO (As-Is)", "Projected TCO (To-Be)", "Cumulative Savings"],
        )


if __name__ == "__main__":
    unittest.main()
