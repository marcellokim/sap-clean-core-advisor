"""Tests for deterministic input validation warnings."""

from __future__ import annotations

import unittest

from models.schemas import CustomerInput, ModuleInfo
from services.analysis_service import _build_validation_warnings
from services.cost_calculator import run_calculation


def _sample_input(**overrides: object) -> CustomerInput:
    payload: dict[str, object] = {
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
        ],
        "annual_it_budget_krw": 50.0,
        "pain_points": "",
        "migration_timeline_months": 18,
    }
    payload.update(overrides)
    return CustomerInput(**payload)


class ValidationWarningsTests(unittest.TestCase):
    def test_duplicate_modules_warning_is_emitted(self) -> None:
        inp = _sample_input(
            modules=[
                ModuleInfo(module_name="FI", customization_level="medium"),
                ModuleInfo(module_name="FI", customization_level="high"),
            ]
        )
        warnings = _build_validation_warnings(inp, run_calculation(inp))
        self.assertTrue(any("중복 모듈" in warning for warning in warnings))

    def test_custom_ratio_program_count_mismatch_warning_is_emitted(self) -> None:
        inp = _sample_input(custom_code_ratio=80.0, num_custom_programs=10)
        warnings = _build_validation_warnings(inp, run_calculation(inp))
        self.assertTrue(any("커스텀 코드 비중이 매우 높지만" in warning for warning in warnings))

    def test_budget_ratio_extreme_warning_is_emitted(self) -> None:
        inp = _sample_input(annual_it_budget_krw=0.2)
        warnings = _build_validation_warnings(inp, run_calculation(inp))
        self.assertTrue(any("TCO/예산 비율" in warning for warning in warnings))


if __name__ == "__main__":
    unittest.main()
