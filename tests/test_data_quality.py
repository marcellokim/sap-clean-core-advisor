"""Tests for calibration dataset quality gate."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from services.data_quality import validate_calibration_rows


def _valid_row() -> dict[str, object]:
    return {
        "company_id": "C1",
        "industry": "제조",
        "erp_version": "ECC 6.0",
        "db_type": "Oracle",
        "num_users": 800,
        "num_custom_programs": 350,
        "custom_code_ratio": 45.0,
        "actual_current_tco": 1.06,
        "actual_projected_tco": 0.95,
        "actual_risk_level": "Medium",
        "migration_duration_months": 18,
    }


class DataQualityTests(unittest.TestCase):
    def test_valid_rows_pass_quality_gate(self) -> None:
        rows = [_valid_row(), {**_valid_row(), "company_id": "C2"}]
        with patch.dict(os.environ, {"CALIBRATION_MIN_SAMPLES": "2"}):
            result = validate_calibration_rows(rows)
        self.assertTrue(result.ok)
        self.assertEqual(result.accepted_rows, 2)

    def test_missing_column_fails_quality_gate(self) -> None:
        bad = _valid_row()
        del bad["industry"]
        with patch.dict(os.environ, {"CALIBRATION_MIN_SAMPLES": "1"}):
            result = validate_calibration_rows([bad])
        self.assertFalse(result.ok)
        self.assertTrue(any("missing columns" in err for err in result.errors))

    def test_insufficient_samples_fails_quality_gate(self) -> None:
        with patch.dict(os.environ, {"CALIBRATION_MIN_SAMPLES": "3"}):
            result = validate_calibration_rows([_valid_row(), {**_valid_row(), "company_id": "C2"}])
        self.assertFalse(result.ok)
        self.assertTrue(any("insufficient samples" in err for err in result.errors))


if __name__ == "__main__":
    unittest.main()
