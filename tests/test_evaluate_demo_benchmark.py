"""Tests for benchmark evaluation reporting helpers."""

from __future__ import annotations

import unittest
from pathlib import Path

from tools.evaluate_demo_benchmark import (
    DEFAULT_FIXTURE_PATH,
    _build_markdown_report,
    _build_tuning_signals,
    evaluate_cases,
    load_benchmark_cases,
)


def _result_row(
    *,
    case_id: str,
    company_name: str,
    score: float,
    risk: str,
    current_tco: float,
    projected_tco: float,
    savings_3yr: float,
    headroom_to_min: float,
    headroom_to_max: float,
) -> dict[str, object]:
    return {
        "case_id": case_id,
        "notes": "",
        "input": {
            "company_name": company_name,
            "industry": "테스트",
        },
        "expected": {
            "score_range": "20.0-30.0",
            "risk_level": risk,
            "rule_ids_any": ["RULE_A"],
            "recommendation_ids_any": ["REC_A"],
        },
        "actual": {
            "clean_core_score": score,
            "score_breakdown": {},
            "risk_level": risk,
            "risk_factors": [],
            "current_annual_tco": current_tco,
            "projected_tco_after_migration": projected_tco,
            "tco_savings_3yr": savings_3yr,
            "applied_rule_ids": ["RULE_A"],
            "recommendation_rule_ids": ["REC_A"],
            "recommendation_texts": ["테스트 추천"],
            "ruleset_profile_id": "base",
            "ruleset_profile_source": "base",
            "ruleset_version": "2026.02.14.v1",
            "calibration_quality": {},
            "resolution_warnings": [],
        },
        "checks": {
            "score_range_hit": True,
            "score_distance_to_range": 0.0,
            "score_headroom_to_min": headroom_to_min,
            "score_headroom_to_max": headroom_to_max,
            "risk_exact_match": True,
            "rule_any_match": True,
            "matched_rule_ids": ["RULE_A"],
            "missing_rule_ids": [],
            "recommendation_any_match": True,
            "matched_recommendation_ids": ["REC_A"],
            "missing_recommendation_ids": [],
            "all_expected_checks_passed": True,
        },
    }


class DemoBenchmarkReportingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.results = [
            _result_row(
                case_id="case-a",
                company_name="A사",
                score=24.0,
                risk="Medium",
                current_tco=1.00,
                projected_tco=0.80,
                savings_3yr=0.60,
                headroom_to_min=4.0,
                headroom_to_max=6.0,
            ),
            _result_row(
                case_id="case-b",
                company_name="B사",
                score=25.0,
                risk="Medium",
                current_tco=1.75,
                projected_tco=1.20,
                savings_3yr=1.65,
                headroom_to_min=1.0,
                headroom_to_max=5.0,
            ),
            _result_row(
                case_id="case-c",
                company_name="C사",
                score=29.0,
                risk="Low",
                current_tco=2.50,
                projected_tco=1.60,
                savings_3yr=2.70,
                headroom_to_min=3.0,
                headroom_to_max=1.0,
            ),
        ]

    def test_build_tuning_signals_summarizes_dispersion_and_headroom(self) -> None:
        signals = _build_tuning_signals(self.results, top_n=2)

        self.assertEqual(signals["score_distribution"]["count"], 3)
        self.assertEqual(signals["score_distribution"]["span"], 5.0)
        self.assertEqual(signals["score_distribution"]["stddev"], 2.2)
        self.assertEqual(signals["current_annual_tco_distribution"]["span"], 1.5)
        self.assertEqual(signals["closest_score_pairs"][0]["left_case_id"], "case-a")
        self.assertEqual(signals["closest_score_pairs"][0]["right_case_id"], "case-b")
        self.assertEqual(signals["closest_score_pairs"][0]["gap"], 1.0)
        self.assertEqual(signals["narrowest_score_headroom_to_min"][0]["case_id"], "case-b")
        self.assertEqual(signals["narrowest_score_headroom_to_max"][0]["case_id"], "case-c")

    def test_markdown_report_includes_tuning_signal_sections(self) -> None:
        summary = {
            "total_cases": len(self.results),
            "metrics": {
                "score_range_hit_rate": {"hits": 3, "total": 3, "rate": 1.0},
                "risk_exact_match_rate": {"hits": 3, "total": 3, "rate": 1.0},
                "rule_any_match_rate": {"hits": 3, "total": 3, "rate": 1.0},
                "recommendation_coverage_rate": {"hits": 3, "total": 3, "rate": 1.0},
                "fully_matched_case_rate": {"hits": 3, "total": 3, "rate": 1.0},
            },
            "tuning_signals": _build_tuning_signals(self.results, top_n=2),
            "industry_differentiation_summary": [
                {
                    "profile_id": "base",
                    "case_count": 3,
                    "average_score": 26.0,
                    "min_score": 24.0,
                    "max_score": 29.0,
                    "score_span": 5.0,
                    "risk_distribution": {"Low": 1, "Medium": 2},
                }
            ],
        }

        report = _build_markdown_report(
            generated_at="2026-03-11T00:00:00Z",
            fixture_path=Path("tests/fixtures/demo_benchmark.yaml"),
            summary=summary,
            results=self.results,
        )

        self.assertIn("## Tuning Signals", report)
        self.assertIn("### Closest Score Pairs", report)
        self.assertIn("case-a", report)
        self.assertIn("case-b", report)
        self.assertIn("### Narrowest Score Headroom (to lower bound)", report)
        self.assertIn("### Narrowest Score Headroom (to upper bound)", report)


class DemoBenchmarkFixtureSignalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cases, cls.metadata = load_benchmark_cases(DEFAULT_FIXTURE_PATH)
        cls.results, cls.summary = evaluate_cases(cls.cases, lang="ko")

    def test_fixture_tracks_expected_closest_score_pairs(self) -> None:
        expected_pairs = self.metadata["tuning_expectations"]["closest_score_pairs"]
        actual_pairs = self.summary["tuning_signals"]["closest_score_pairs"]

        self.assertEqual(len(actual_pairs), len(expected_pairs))
        for expected, actual in zip(expected_pairs, actual_pairs):
            self.assertEqual(actual["left_case_id"], expected["left_case_id"])
            self.assertEqual(actual["right_case_id"], expected["right_case_id"])
            self.assertGreaterEqual(actual["gap"], expected["minimum_gap"])

    def test_fixture_closest_pair_cases_dominate_tightest_headroom_signals(self) -> None:
        expected_pairs = self.metadata["tuning_expectations"]["closest_score_pairs"]
        expected_case_ids = {
            case_id
            for pair in expected_pairs
            for case_id in (pair["left_case_id"], pair["right_case_id"])
        }

        signals = _build_tuning_signals(self.results, top_n=len(expected_case_ids))

        self.assertEqual(
            {item["case_id"] for item in signals["narrowest_score_headroom_to_min"]},
            expected_case_ids,
        )
        self.assertEqual(
            {item["case_id"] for item in signals["narrowest_score_headroom_to_max"]},
            expected_case_ids,
        )
        self.assertTrue(
            all(item["headroom"] == 0.8 for item in signals["narrowest_score_headroom_to_min"])
        )
        self.assertTrue(
            all(item["headroom"] == 0.8 for item in signals["narrowest_score_headroom_to_max"])
        )


if __name__ == "__main__":
    unittest.main()
