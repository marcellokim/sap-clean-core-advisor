"""Tests for citation coverage validator."""

from __future__ import annotations

import unittest

from models.schemas import EvidenceItem
from services.domain.claim_extractor import ReportClaim
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

    def test_low_issue_when_report_claims_exceed_evidence_claims(self) -> None:
        report_claims = [
            ReportClaim(
                section="executive_summary",
                line_no=1,
                claim_type="numeric",
                text="Clean Core 점수 42.6/100",
            ),
            ReportClaim(
                section="detailed_report",
                line_no=2,
                claim_type="statement",
                text="- 권고안 1",
            ),
        ]
        evidence_item = EvidenceItem(
            claim_id="CLAIM_01",
            claim_text="Clean Core 점수 42.6/100",
            evidence_grade="A",
            input_facts=["Clean Core 점수 42.6/100"],
            rule_ids=["REC_SCORE_LT_60"],
            rag_sources=[],
            reference_source_ids=["SRC_1"],
            generation_mode="fallback",
        )
        issues, metrics = validate_citation_coverage(
            [evidence_item],
            report_claims,
            strict_reference_ids=True,
        )
        self.assertEqual(metrics.total_report_claims, 2)
        self.assertEqual(metrics.uncovered_report_claims, 1)
        self.assertTrue(any(issue.code == "CITATION_REPORT_CLAIMS_UNCOVERED" for issue in issues))

    def test_report_claims_must_match_evidence_content_not_only_count(self) -> None:
        report_claims = [
            ReportClaim(
                section="executive_summary",
                line_no=1,
                claim_type="numeric",
                text="Clean Core score is 99/100",
            ),
            ReportClaim(
                section="detailed_report",
                line_no=2,
                claim_type="statement",
                text="- Contract savings are guaranteed next quarter",
            ),
        ]
        issues, metrics = validate_citation_coverage(
            [
                _item("CLAIM_01", refs=["SRC_1"]),
                _item("CLAIM_02", refs=["SRC_2"]),
            ],
            report_claims,
            strict_reference_ids=True,
        )

        self.assertEqual(metrics.total_report_claims, 2)
        self.assertEqual(metrics.uncovered_report_claims, 2)
        self.assertTrue(any(issue.code == "CITATION_REPORT_CLAIMS_UNCOVERED" for issue in issues))


if __name__ == "__main__":
    unittest.main()
