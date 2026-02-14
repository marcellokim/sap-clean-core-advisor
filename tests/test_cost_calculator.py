"""Tests for rule-based cost calculator."""

from __future__ import annotations

import unittest

from models.schemas import CustomerInput, ModuleInfo
from services.cost_calculator import calculate_tco, run_calculation


def _sample_input(**overrides: object) -> CustomerInput:
    data: dict[str, object] = {
        "company_name": "테스트제조",
        "industry": "제조",
        "erp_version": "ECC 6.0",
        "db_type": "Oracle",
        "db_size_gb": 500.0,
        "num_users": 800,
        "num_custom_programs": 350,
        "custom_code_ratio": 45.0,
        "modules": [
            ModuleInfo(module_name="FI", customization_level="medium"),
            ModuleInfo(module_name="CO", customization_level="medium"),
            ModuleInfo(module_name="MM", customization_level="medium"),
            ModuleInfo(module_name="SD", customization_level="medium"),
        ],
        "annual_it_budget_krw": 50.0,
        "pain_points": "결산 지연",
        "migration_timeline_months": 18,
    }
    data.update(overrides)
    return CustomerInput(**data)


class CostCalculatorTests(unittest.TestCase):
    def test_tco_matches_expected_numbers(self) -> None:
        current_tco, projected_tco, savings_3yr = calculate_tco(_sample_input())
        self.assertAlmostEqual(current_tco, 1.06, places=2)
        self.assertAlmostEqual(projected_tco, 0.95, places=2)
        self.assertAlmostEqual(savings_3yr, 0.33, places=2)

    def test_clean_core_score_and_breakdown_are_consistent(self) -> None:
        result = run_calculation(_sample_input())
        self.assertAlmostEqual(result.clean_core_score, 42.6, places=1)
        self.assertEqual(result.score_breakdown["custom_code"], 32.5)
        self.assertEqual(result.score_breakdown["erp_version"], 40.0)
        self.assertEqual(result.score_breakdown["database"], 45.0)
        self.assertEqual(result.score_breakdown["module_complexity"], 58.0)

    def test_budget_pressure_risk_is_added_for_high_tco_ratio(self) -> None:
        low_budget_input = _sample_input(annual_it_budget_krw=1.0)
        result = run_calculation(low_budget_input)
        self.assertEqual(result.risk_level, "High")
        self.assertTrue(any("연간 IT 예산" in risk for risk in result.risk_factors))


if __name__ == "__main__":
    unittest.main()
