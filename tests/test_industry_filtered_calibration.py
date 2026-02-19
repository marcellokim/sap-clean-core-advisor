"""Tests for industry-aware row filtering in calibration pipeline."""

from __future__ import annotations

import unittest

from services.industry_filter import filter_rows_by_industry


class IndustryFilteredCalibrationTests(unittest.TestCase):
    def test_filter_rows_by_industry_keeps_matching_profiles(self) -> None:
        rows = [
            {"company_id": "A", "industry": "제조"},
            {"company_id": "B", "industry": "manufacturing"},
            {"company_id": "C", "industry": "retail"},
            {"company_id": "D", "industry": "금융"},
        ]
        result = filter_rows_by_industry(rows, "manufacturing")
        self.assertEqual(result.target_profile, "manufacturing")
        self.assertEqual(result.total_rows, 4)
        self.assertEqual(result.matched_rows, 2)
        self.assertEqual(result.excluded_rows, 2)
        self.assertEqual([r["company_id"] for r in result.rows], ["A", "B"])

    def test_filter_rows_by_industry_unknown_target_maps_to_base(self) -> None:
        rows = [
            {"company_id": "A", "industry": "제조"},
            {"company_id": "B", "industry": "unknown-industry"},
        ]
        result = filter_rows_by_industry(rows, "unknown-industry")
        self.assertEqual(result.target_profile, "base")
        self.assertEqual(result.matched_rows, 1)
        self.assertEqual(result.rows[0]["company_id"], "B")


if __name__ == "__main__":
    unittest.main()

