"""Tests for deterministic recommendation extraction behavior."""

from __future__ import annotations

import unittest

from models.schemas import CustomerInput, ModuleInfo
from services.cost_calculator import run_calculation
from services.domain.recommendation_engine import extract_recommendations


def _low_risk_input() -> CustomerInput:
    return CustomerInput(
        company_name="테스트리테일",
        industry="유통",
        erp_version="S/4HANA 2023",
        db_type="SAP HANA",
        db_size_gb=900.0,
        num_users=650,
        num_custom_programs=85,
        custom_code_ratio=14.0,
        modules=[
            ModuleInfo(module_name="FI", customization_level="low"),
            ModuleInfo(module_name="MM", customization_level="low"),
            ModuleInfo(module_name="SD", customization_level="medium"),
            ModuleInfo(module_name="EWM", customization_level="low"),
        ],
        annual_it_budget_krw=55.0,
        pain_points="프로모션 시즌 성능 저하",
        migration_timeline_months=24,
    )


class RecommendationEngineTests(unittest.TestCase):
    def test_low_risk_case_returns_at_least_three_actions(self) -> None:
        inp = _low_risk_input()
        calc = run_calculation(inp)
        traces = extract_recommendations(calc, inp, lang="ko")

        self.assertGreaterEqual(len(traces), 3)
        rule_ids = {rid for trace in traces for rid in trace.rule_ids}
        low_risk_boosters = {
            "REC_LOW_RISK_GOVERNANCE",
            "REC_LOW_RISK_KPI_MONITORING",
            "REC_LOW_RISK_ROADMAP",
        }
        self.assertGreaterEqual(len(rule_ids & low_risk_boosters), 2)

    def test_pain_points_add_contextual_recommendations(self) -> None:
        inp = _low_risk_input().model_copy(
            update={"pain_points": "월마감 지연과 업그레이드 호환성 문제가 반복됩니다."}
        )
        calc = run_calculation(inp)
        traces = extract_recommendations(calc, inp, lang="ko")

        rule_ids = {rid for trace in traces for rid in trace.rule_ids}
        self.assertIn("REC_PAIN_FIN_CLOSE", rule_ids)
        self.assertIn("REC_PAIN_UPGRADE_COMPAT", rule_ids)


if __name__ == "__main__":
    unittest.main()
