"""Tests for evidence ledger grading rules."""

from __future__ import annotations

import unittest

from services.analysis_service import _grade_evidence


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


if __name__ == "__main__":
    unittest.main()
