"""Tests for shared report pre-confirm validation helpers."""

from __future__ import annotations

import unittest

from models.schemas import AdvisorOutput, EvidenceItem
from services.application.report_preflight import (
    collect_preconfirm_issues,
    run_preconfirm_validation,
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
        risk_factors=["risk-a"],
        recommendations=["rec-a"],
        tech_debt_breakdown={"FI": 10.0},
        executive_summary=(
            "Clean Core 점수 42.6/100\n"
            "현재 연간 TCO 1.06억원\n"
            "전환 후 연간 TCO 0.95억원\n"
            "3년 누적 절감액 0.33억원\n"
        ),
        detailed_report="## 1. 현황 분석\n- 권고안 1",
        evidence_ledger=[
            EvidenceItem(
                claim_id="CLAIM_01",
                claim_text="Clean Core 점수 42.6/100 현재 연간 TCO 1.06억원",
                evidence_grade="A",
                input_facts=["Clean Core 점수 42.6/100", "현재 연간 TCO 1.06억원"],
                rule_ids=["REC_SCORE_LT_60"],
                rag_sources=[],
                reference_source_ids=["SRC_SAP_CLEAN_CORE"],
                generation_mode="fallback",
            )
        ],
        generation_mode="fallback",
        analysis_id="test-id",
    )


class ReportPreflightTests(unittest.TestCase):
    def test_collect_preconfirm_issues_includes_report_claim_metrics(self) -> None:
        issues, metrics = collect_preconfirm_issues(
            _sample_output(),
            analysis_date="2026-04-26",
        )

        self.assertGreater(metrics.total_report_claims, 0)
        self.assertGreater(metrics.uncovered_report_claims, 0)
        self.assertTrue(
            any(issue.code == "CITATION_REPORT_CLAIMS_UNCOVERED" for issue in issues)
        )

    def test_run_preconfirm_validation_warns_on_report_claim_coverage(self) -> None:
        updated, _issues, metrics = run_preconfirm_validation(
            _sample_output(),
            analysis_date="2026-04-26",
            validation_warnings=[],
        )

        self.assertIsNotNone(metrics)
        self.assertTrue(
            any(
                warning.startswith("REPORT_PRECONFIRM_REPORT_CLAIM_COVERAGE")
                for warning in updated.validation_warnings
            )
        )


if __name__ == "__main__":
    unittest.main()
