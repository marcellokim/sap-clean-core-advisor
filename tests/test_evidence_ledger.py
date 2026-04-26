"""Tests for evidence ledger grading rules."""

from __future__ import annotations

import unittest

from services.analysis_service import _grade_evidence
from services.domain.evidence_engine import build_evidence_ledger
from services.domain.recommendation_engine import RecommendationTrace
from services.rag_pipeline import RAGContextBundle


class EvidenceLedgerTests(unittest.TestCase):
    def test_grade_a_when_facts_and_rules_exist(self) -> None:
        grade = _grade_evidence(
            input_facts=["fact"],
            rule_ids=["RULE_1"],
            rag_sources=["source.md"],
        )
        self.assertEqual(grade, "A")

    def test_grade_b_when_only_rules_exist(self) -> None:
        grade = _grade_evidence(
            input_facts=[],
            rule_ids=["RULE_1"],
            rag_sources=[],
        )
        self.assertEqual(grade, "B")

    def test_grade_c_when_only_rag_exists(self) -> None:
        grade = _grade_evidence(
            input_facts=[],
            rule_ids=[],
            rag_sources=["source.md"],
        )
        self.assertEqual(grade, "C")

    def test_grade_d_when_no_evidence_exists(self) -> None:
        grade = _grade_evidence(
            input_facts=[],
            rule_ids=[],
            rag_sources=[],
        )
        self.assertEqual(grade, "D")

    def test_rag_sources_add_source_catalog_reference_ids(self) -> None:
        ledger = build_evidence_ledger(
            [
                RecommendationTrace(
                    text="Clean Core strategy extension pattern",
                    rule_ids=[],
                    input_facts=[],
                )
            ],
            generation_mode="llm",
            rag_bundle=RAGContextBundle(
                context="[출처: clean_core_strategy.md]\nClean Core strategy extension pattern",
                sources=["clean_core_strategy.md"],
                chunk_count=1,
            ),
        )

        self.assertEqual(ledger[0].rag_sources, ["clean_core_strategy.md"])
        self.assertIn("SRC_SAP_CLEAN_CORE", ledger[0].reference_source_ids)


if __name__ == "__main__":
    unittest.main()
