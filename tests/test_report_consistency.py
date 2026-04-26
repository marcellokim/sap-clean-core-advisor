"""Tests for report numeric consistency validator."""

from __future__ import annotations

import unittest

from models.schemas import AdvisorOutput
from services.domain.report_consistency import validate_report_consistency


def _sample_output(executive_summary: str, detailed_report: str) -> AdvisorOutput:
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
        risk_factors=["risk-a"],
        recommendations=["rec-a"],
        executive_summary=executive_summary,
        detailed_report=detailed_report,
        tech_debt_breakdown={"FI": 10.0},
        generation_mode="fallback",
        analysis_id="test-id",
    )


class ReportConsistencyTests(unittest.TestCase):
    def test_no_high_issue_when_numbers_match(self) -> None:
        output = _sample_output(
            executive_summary=(
                "Clean Core 점수 42.6/100\n"
                "현재 연간 TCO 1.06억원\n"
                "전환 후 연간 TCO 0.95억원\n"
                "3년 누적 절감액 0.33억원\n"
            ),
            detailed_report="## 1. 현황 분석\n- 보고서 상세",
        )
        issues = validate_report_consistency(output)
        self.assertFalse(any(issue.severity == "HIGH" for issue in issues))

    def test_high_issue_when_score_mismatch(self) -> None:
        output = _sample_output(
            executive_summary=(
                "Clean Core 점수 55.0/100\n"
                "현재 연간 TCO 1.06억원\n"
                "전환 후 연간 TCO 0.95억원\n"
                "3년 누적 절감액 0.33억원\n"
            ),
            detailed_report="## 1. 현황 분석\n- 보고서 상세",
        )
        issues = validate_report_consistency(output)
        self.assertTrue(any(issue.code == "REPORT_METRIC_MISMATCH_CLEAN_CORE_SCORE" for issue in issues))

    def test_high_issue_when_later_metric_contradicts_first_match(self) -> None:
        output = _sample_output(
            executive_summary=(
                "Clean Core 점수 42.6/100\n"
                "현재 연간 TCO 1.06억원\n"
                "전환 후 연간 TCO 0.95억원\n"
                "3년 누적 절감액 0.33억원\n"
            ),
            detailed_report=(
                "## 1. 현황 분석\n"
                "- Clean Core Score 10.0/100\n"
                "- 현재 연간 TCO 99.0억원\n"
            ),
        )
        issues = validate_report_consistency(output)
        issue_codes = {issue.code for issue in issues}
        self.assertIn("REPORT_METRIC_MISMATCH_CLEAN_CORE_SCORE", issue_codes)
        self.assertIn("REPORT_METRIC_MISMATCH_CURRENT_ANNUAL_TCO", issue_codes)


if __name__ == "__main__":
    unittest.main()
