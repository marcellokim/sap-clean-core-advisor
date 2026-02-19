"""Tests for generated ruleset activation guard."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from services.ruleset_loader import resolve_ruleset_profile


def _payload(profile_id: str) -> dict[str, object]:
    return {
        "ruleset_version": "test.v1",
        "profile_id": profile_id,
        "calibration_quality": {},
        "module_weights": {"FI": 1.0},
        "customization_score": {"low": 0.3, "medium": 0.6, "high": 1.0},
        "score_weights": {
            "custom_code": 0.35,
            "erp_version": 0.25,
            "database": 0.15,
            "module_complexity": 0.25,
        },
        "erp_version_scores": {"ECC 6.0": 40.0},
        "database_scores": {"hana": 90.0, "oracle": 45.0, "sql": 40.0, "other": 35.0},
        "formula": {
            "custom_code_multiplier": 1.5,
            "module_severity_multiplier": 50.0,
            "module_count_penalty_per_module": 3.0,
            "module_count_penalty_cap": 30.0,
            "module_complexity_empty_score": 80.0,
        },
        "tco": {
            "infra_cost_per_user": 0.0003,
            "custom_maintenance_per_program": 0.0005,
            "license_cost_per_user": 0.0008,
            "db_cost_per_gb": 0.00002,
            "cloud_infra_savings_rate": 0.35,
            "clean_core_custom_savings_rate": 0.5,
            "s4_license_change_rate": 1.1,
        },
        "risk_thresholds": {
            "custom_ratio_medium": 30.0,
            "custom_ratio_high": 60.0,
            "timeline_months_tight": 12,
            "timeline_custom_programs_tight": 200,
            "db_size_large_gb": 5000.0,
            "budget_ratio_medium": 0.7,
            "budget_ratio_high": 1.0,
            "risk_level_score_high": 30.0,
            "risk_level_score_medium": 60.0,
            "risk_factor_count_high": 4,
            "risk_factor_count_medium": 2,
        },
    }


class RulesetActivationTests(unittest.TestCase):
    def setUp(self) -> None:
        resolve_ruleset_profile.cache_clear()

    def test_generated_ruleset_disabled_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "rulesets"
            (root / "industries").mkdir(parents=True)
            (root / "generated").mkdir(parents=True)
            (root / "base.yaml").write_text(json.dumps(_payload("base")), encoding="utf-8")
            (root / "industries" / "manufacturing.yaml").write_text(
                json.dumps(_payload("industry-manufacturing")),
                encoding="utf-8",
            )
            (root / "generated" / "manufacturing.yaml").write_text(
                json.dumps(_payload("generated-manufacturing")),
                encoding="utf-8",
            )
            with patch.dict(
                os.environ,
                {
                    "RULESET_DIR": str(root),
                    "RULESET_GENERATED_DIR": str(root / "generated"),
                    "RULESET_ALLOW_GENERATED": "false",
                },
            ):
                resolve_ruleset_profile.cache_clear()
                resolution = resolve_ruleset_profile("제조")
                self.assertEqual(resolution.profile.profile_source, "industry")
                self.assertEqual(resolution.profile.profile_id, "industry-manufacturing")

    def test_generated_ruleset_enabled_when_flag_true(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "rulesets"
            (root / "industries").mkdir(parents=True)
            (root / "generated").mkdir(parents=True)
            (root / "base.yaml").write_text(json.dumps(_payload("base")), encoding="utf-8")
            (root / "industries" / "manufacturing.yaml").write_text(
                json.dumps(_payload("industry-manufacturing")),
                encoding="utf-8",
            )
            (root / "generated" / "manufacturing.yaml").write_text(
                json.dumps(_payload("generated-manufacturing")),
                encoding="utf-8",
            )
            with patch.dict(
                os.environ,
                {
                    "RULESET_DIR": str(root),
                    "RULESET_GENERATED_DIR": str(root / "generated"),
                    "RULESET_ALLOW_GENERATED": "true",
                },
            ):
                resolve_ruleset_profile.cache_clear()
                resolution = resolve_ruleset_profile("제조")
                self.assertEqual(resolution.profile.profile_source, "generated")
                self.assertEqual(resolution.profile.profile_id, "generated-manufacturing")


if __name__ == "__main__":
    unittest.main()

