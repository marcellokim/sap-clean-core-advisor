"""Date claim validator for report pre-confirm checks."""

from __future__ import annotations

import re

from services.domain.verification_types import ValidationIssue


_LABELED_REPORT_DATE_PATTERN = re.compile(
    r"(?:일자|날짜|보고\s*일자|작성일|기준일)\s*[:：]?\s*(20\d{2})년\s*(\d{1,2})월\s*(\d{1,2})일"
)
_ISO_DATE_PATTERN = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")


def validate_date_claims(
    executive_summary: str,
    detailed_report: str,
    *,
    analysis_date: str,
) -> list[ValidationIssue]:
    """Validate report-level date claims."""
    combined = f"{executive_summary}\n{detailed_report}".strip()
    lines = combined.splitlines()[:20]
    issues: list[ValidationIssue] = []

    expected_year = analysis_date[:4]
    for line in lines:
        for year, month, day in _LABELED_REPORT_DATE_PATTERN.findall(line):
            normalized = f"{year}-{int(month):02d}-{int(day):02d}"
            if normalized != analysis_date:
                issues.append(
                    ValidationIssue(
                        severity="HIGH",
                        code="REPORT_DATE_MISMATCH",
                        message=f"보고서 기준일 불일치 (report={normalized}, expected={analysis_date})",
                    )
                )
                break
            if year != expected_year:
                issues.append(
                    ValidationIssue(
                        severity="HIGH",
                        code="REPORT_YEAR_MISMATCH",
                        message=f"보고서 연도 불일치 (report={year}, expected={expected_year})",
                    )
                )
                break

    allowed_iso_dates = {analysis_date, "2027-12-31", "2030-12-31"}
    for iso_date in _ISO_DATE_PATTERN.findall(combined):
        if iso_date not in allowed_iso_dates:
            issues.append(
                ValidationIssue(
                    severity="LOW",
                    code="UNMAPPED_DATE_CLAIM",
                    message=f"출처 매핑 확인이 필요한 날짜 claim: {iso_date}",
                )
            )
    return issues
