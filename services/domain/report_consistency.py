"""Report numeric consistency validator."""

from __future__ import annotations

import re

from models.schemas import AdvisorOutput
from services.domain.verification_types import ValidationIssue


_FLOAT_PATTERN = r"[0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?"

_SCORE_PATTERNS = [
    re.compile(
        rf"(?:Clean\s*Core(?:\s*점수|\s*Score)?)[^0-9]{{0,20}}({_FLOAT_PATTERN})\s*/\s*100",
        re.IGNORECASE,
    ),
]
_CURRENT_TCO_PATTERNS = [
    re.compile(
        rf"(?:현재(?:\s*연간)?\s*TCO|Current(?:\s*Annual)?\s*TCO)[^0-9]{{0,20}}({_FLOAT_PATTERN})",
        re.IGNORECASE,
    ),
]
_PROJECTED_TCO_PATTERNS = [
    re.compile(
        rf"(?:전환\s*후(?:\s*연간)?\s*TCO|Projected(?:\s*Annual)?\s*TCO|To-Be)[^0-9]{{0,20}}({_FLOAT_PATTERN})",
        re.IGNORECASE,
    ),
]
_SAVINGS_PATTERNS = [
    re.compile(
        rf"(?:3년\s*누적(?:\s*TCO)?\s*절감(?:액)?|3-year\s*(?:cumulative\s*)?savings)[^0-9+\-]{{0,20}}([+\-]?{_FLOAT_PATTERN})",
        re.IGNORECASE,
    ),
]


def _to_float(raw: str) -> float | None:
    try:
        return float(raw.replace(",", ""))
    except Exception:
        return None


def _extract_numeric(patterns: list[re.Pattern[str]], text: str) -> float | None:
    for pattern in patterns:
        match = pattern.search(text)
        if not match:
            continue
        candidate = match.group(1)
        parsed = _to_float(candidate)
        if parsed is not None:
            return parsed
    return None


def _validate_metric(
    issues: list[ValidationIssue],
    *,
    text: str,
    field_name: str,
    expected: float,
    patterns: list[re.Pattern[str]],
    tolerance: float,
) -> None:
    found = _extract_numeric(patterns, text)
    if found is None:
        issues.append(
            ValidationIssue(
                severity="LOW",
                code=f"REPORT_METRIC_NOT_FOUND_{field_name.upper()}",
                message=f"보고서에서 {field_name} 수치를 찾지 못했습니다.",
            )
        )
        return

    if abs(found - expected) > tolerance:
        issues.append(
            ValidationIssue(
                severity="HIGH",
                code=f"REPORT_METRIC_MISMATCH_{field_name.upper()}",
                message=(
                    f"{field_name} 수치 불일치 (report={found:.2f}, expected={expected:.2f}, tolerance={tolerance})"
                ),
            )
        )


def validate_report_consistency(output: AdvisorOutput) -> list[ValidationIssue]:
    """Check numeric consistency between report text and deterministic output."""
    text = f"{output.executive_summary}\n{output.detailed_report}"
    issues: list[ValidationIssue] = []

    _validate_metric(
        issues,
        text=text,
        field_name="clean_core_score",
        expected=output.clean_core_score,
        patterns=_SCORE_PATTERNS,
        tolerance=0.2,
    )
    _validate_metric(
        issues,
        text=text,
        field_name="current_annual_tco",
        expected=output.current_annual_tco,
        patterns=_CURRENT_TCO_PATTERNS,
        tolerance=0.2,
    )
    _validate_metric(
        issues,
        text=text,
        field_name="projected_tco_after_migration",
        expected=output.projected_tco_after_migration,
        patterns=_PROJECTED_TCO_PATTERNS,
        tolerance=0.2,
    )
    _validate_metric(
        issues,
        text=text,
        field_name="tco_savings_3yr",
        expected=output.tco_savings_3yr,
        patterns=_SAVINGS_PATTERNS,
        tolerance=0.25,
    )
    return issues
