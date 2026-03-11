"""Tests for industry normalization and canonical profile resolution."""

from __future__ import annotations

import unittest

from services.industry_mapper import resolve_industry_profile


class IndustryMapperTests(unittest.TestCase):
    def test_korean_manufacturing_maps_to_canonical_profile(self) -> None:
        result = resolve_industry_profile("제조")
        self.assertTrue(result.matched)
        self.assertEqual(result.profile_key, "manufacturing")

    def test_ui_retail_label_maps_to_retail_profile(self) -> None:
        result = resolve_industry_profile("유통/리테일")
        self.assertTrue(result.matched)
        self.assertEqual(result.profile_key, "retail")

    def test_ui_finance_label_maps_to_finance_profile(self) -> None:
        result = resolve_industry_profile("금융/보험")
        self.assertTrue(result.matched)
        self.assertEqual(result.profile_key, "finance")

    def test_unknown_industry_falls_back_to_base(self) -> None:
        result = resolve_industry_profile("Space Mining")
        self.assertFalse(result.matched)
        self.assertEqual(result.profile_key, "base")


if __name__ == "__main__":
    unittest.main()
