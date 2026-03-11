"""Regression tests for calibrated scoring, risk, and recommendation heuristics."""

from __future__ import annotations

import unittest

from models.schemas import CustomerInput, ModuleInfo
from services.cost_calculator import run_calculation
from services.domain.recommendation_engine import extract_recommendations


def _base_input(**overrides: object) -> CustomerInput:
    data: dict[str, object] = {
        "company_name": "회귀테스트사",
        "industry": "제조",
        "erp_version": "S/4HANA 2023",
        "db_type": "SAP HANA",
        "db_size_gb": 800.0,
        "num_users": 1000,
        "num_custom_programs": 120,
        "custom_code_ratio": 18.0,
        "modules": [
            ModuleInfo(module_name="FI", customization_level="low"),
            ModuleInfo(module_name="MM", customization_level="low"),
        ],
        "annual_it_budget_krw": 40.0,
        "pain_points": "",
        "migration_timeline_months": 24,
    }
    data.update(overrides)
    return CustomerInput(**data)


def _rule_ids(traces: list) -> set[str]:
    return {rule_id for trace in traces for rule_id in trace.rule_ids}


class CalibrationRegressionTests(unittest.TestCase):
    def test_large_oracle_database_has_lower_database_score_than_hana(self) -> None:
        hana_result = run_calculation(_base_input(db_type="SAP HANA", db_size_gb=4000.0))
        oracle_result = run_calculation(_base_input(db_type="Oracle", db_size_gb=4000.0))

        self.assertLess(
            oracle_result.score_breakdown["database"],
            hana_result.score_breakdown["database"],
        )
        self.assertIn("SCORE_DATABASE_SIZE_MODIFIER_V1", oracle_result.applied_rule_ids)

    def test_dual_axis_pain_points_emit_dual_axis_risk_rule(self) -> None:
        result = run_calculation(
            _base_input(pain_points="월마감 지연과 업그레이드 호환성 문제가 반복됩니다.")
        )

        self.assertIn("RISK_PAIN_POINTS_DUAL_AXIS", result.applied_rule_ids)

    def test_multi_axis_pain_points_generate_matching_recommendations(self) -> None:
        inp = _base_input(pain_points="월마감 지연, 업그레이드 호환성, 성능 저하가 반복됩니다.")
        traces = extract_recommendations(run_calculation(inp), inp, lang="ko")

        rule_ids = _rule_ids(traces)
        self.assertTrue(
            {"REC_PAIN_FIN_CLOSE", "REC_PAIN_PERFORMANCE", "REC_PAIN_UPGRADE_COMPAT"}
            <= rule_ids
        )

    def test_single_high_custom_module_adds_presence_risk_rule(self) -> None:
        result = run_calculation(
            _base_input(
                modules=[
                    ModuleInfo(module_name="FI", customization_level="high"),
                    ModuleInfo(module_name="MM", customization_level="low"),
                ]
            )
        )

        self.assertIn("RISK_HIGH_CUSTOM_MODULES_PRESENT", result.applied_rule_ids)

    def test_high_custom_module_recommends_btp_containment(self) -> None:
        inp = _base_input(
            modules=[
                ModuleInfo(module_name="FI", customization_level="high"),
                ModuleInfo(module_name="MM", customization_level="low"),
            ]
        )
        traces = extract_recommendations(run_calculation(inp), inp, lang="ko")

        self.assertIn("REC_HIGH_CUSTOM_MODULE_BTP", _rule_ids(traces))

    def test_near_tight_timeline_adds_buffer_low_risk_rule(self) -> None:
        result = run_calculation(
            _base_input(migration_timeline_months=16, num_custom_programs=140)
        )

        self.assertIn("RISK_TIMELINE_BUFFER_LOW", result.applied_rule_ids)


if __name__ == "__main__":
    unittest.main()
