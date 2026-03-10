"""Tests for date claim validator."""

from __future__ import annotations

import unittest

from services.domain.date_claim_validator import validate_date_claims


class DateClaimValidatorTests(unittest.TestCase):
    def test_report_date_mismatch_is_high(self) -> None:
        issues = validate_date_claims(
            executive_summary="보고 일자: 2024년 5월 27일",
            detailed_report="상세 본문",
            analysis_date="2026-03-09",
        )
        self.assertTrue(any(issue.code == "REPORT_DATE_MISMATCH" for issue in issues))

    def test_known_maintenance_dates_are_allowed(self) -> None:
        issues = validate_date_claims(
            executive_summary="BS7 메인스트림 종료일: 2027-12-31",
            detailed_report="Extended Maintenance: 2030-12-31",
            analysis_date="2026-03-09",
        )
        self.assertFalse(any(issue.severity == "HIGH" for issue in issues))


if __name__ == "__main__":
    unittest.main()
