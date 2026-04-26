"""Tests for rule-to-source mapping completeness."""

from __future__ import annotations

import unittest

from services.reference_mapper import RAG_SOURCE_REFERENCE_MAP, get_rule_reference_map
from tools.verify_sources import load_source_catalog


REQUIRED_RULE_IDS = [
    "REC_SCORE_LT_30",
    "REC_SCORE_LT_60",
    "REC_BS7_MAINSTREAM_END_2027",
    "INFO_BS7_EXTENDED_MAINT_AVAILABLE_2030",
    "REC_DB_TO_HANA",
    "REC_CUSTOM_RATIO_OVER_40",
    "REC_TCO_SAVINGS_POSITIVE",
    "REC_BUDGET_RATIO_OVER_100",
    "REC_BUDGET_RATIO_OVER_70",
    "REC_HIGH_CUSTOM_MODULE_BTP",
    "REC_TIMELINE_TIGHT_PHASED",
    "REC_DEFAULT_BASELINE",
    "REC_LOW_RISK_GOVERNANCE",
    "REC_LOW_RISK_KPI_MONITORING",
    "REC_LOW_RISK_ROADMAP",
    "RISK_CUSTOM_RATIO_HIGH",
    "RISK_CUSTOM_RATIO_MEDIUM",
    "RISK_ERP_EOS_IMMINENT",
    "RISK_BS7_MAINSTREAM_END_2027",
    "RISK_DB_NOT_HANA",
    "RISK_HIGH_CUSTOM_MODULES_3PLUS",
    "RISK_TIMELINE_TOO_SHORT_FOR_CUSTOM",
    "RISK_DB_SIZE_LARGE",
    "RISK_BUDGET_RATIO_OVER_100",
    "RISK_BUDGET_RATIO_OVER_70",
    "RISK_LEVEL_HIGH_RULE",
    "RISK_LEVEL_MEDIUM_RULE",
    "RISK_LEVEL_LOW_RULE",
]


class RuleReferenceMapTests(unittest.TestCase):
    def test_all_required_rules_have_source_mapping(self) -> None:
        mapping = get_rule_reference_map()
        missing = [rule_id for rule_id in REQUIRED_RULE_IDS if rule_id not in mapping]
        self.assertFalse(missing, f"Missing rule->source mapping: {missing}")
        for rule_id in REQUIRED_RULE_IDS:
            self.assertTrue(mapping[rule_id], f"Empty source mapping for {rule_id}")

    def test_mapped_source_ids_exist_in_catalog(self) -> None:
        mapping = get_rule_reference_map()
        catalog_ids = {
            str(item["source_id"])
            for item in load_source_catalog()
        }
        missing_source_ids: set[str] = set()
        for source_ids in mapping.values():
            for source_id in source_ids:
                if source_id not in catalog_ids:
                    missing_source_ids.add(source_id)
        self.assertFalse(
            missing_source_ids,
            f"Missing source IDs in docs/sources.yaml: {sorted(missing_source_ids)}",
        )

    def test_rag_source_reference_ids_exist_in_catalog(self) -> None:
        catalog_ids = {
            str(item["source_id"])
            for item in load_source_catalog()
        }
        missing_source_ids = {
            source_id
            for source_ids in RAG_SOURCE_REFERENCE_MAP.values()
            for source_id in source_ids
            if source_id not in catalog_ids
        }
        self.assertFalse(
            missing_source_ids,
            f"Missing RAG source IDs in docs/sources.yaml: {sorted(missing_source_ids)}",
        )


if __name__ == "__main__":
    unittest.main()
