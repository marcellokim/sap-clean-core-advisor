"""Tests for citation coverage validator."""

from __future__ import annotations

import unittest

from models.schemas import EvidenceItem
from services.domain.citation_validator import validate_citation_coverage


def _item(
    claim_id: str,
    grade: str = "A",
    refs: list[str] | None = None,
) -> EvidenceItem:
    return EvidenceItem(
        claim_id=claim_id,
        claim_text=f"{claim_id} text",
        evidence_grade=grade,  # type: ignore[arg-type]
        input_facts=["fact"],
        rule_ids=["RULE_1"],
        rag_sources=["source_a"],
        reference_source_ids=refs or [],
        generation_mode="fallback",
    )


class CitationValidatorTests(unittest.TestCase):
    def test_high_issue_when_reference_ids_missing(self) -> None:
        issues, metrics = validate_citation_coverage(
            [_item("CLAIM_01", refs=["SRC_1"]), _item("CLAIM_02", refs=[])],
            strict_reference_ids=True,
        )
        self.assertEqual(metrics.total_claims, 2)
        self.assertEqual(metrics.with_reference_source_ids, 1)
        self.assertTrue(any(issue.severity == "HIGH" for issue in issues))

    def test_medium_issue_when_d_grade_exists(self) -> None:
        issues, _ = validate_citation_coverage(
            [_item("CLAIM_01", grade="D", refs=["SRC_1"])],
            strict_reference_ids=True,
        )
        self.assertTrue(any(issue.code == "CITATION_D_GRADE_PRESENT" for issue in issues))

    def test_no_high_issue_when_all_claims_have_sources(self) -> None:
        issues, metrics = validate_citation_coverage(
            [_item("CLAIM_01", refs=["SRC_1"]), _item("CLAIM_02", refs=["SRC_2"])],
            strict_reference_ids=True,
        )
        self.assertEqual(metrics.coverage_ratio, 1.0)
        self.assertFalse(any(issue.severity == "HIGH" for issue in issues))


if __name__ == "__main__":
    unittest.main()
