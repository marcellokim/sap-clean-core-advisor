"""Industry-based filtering helpers for calibration/backtest datasets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from services.industry_mapper import resolve_industry_profile


@dataclass(frozen=True)
class IndustryFilterResult:
    """Industry filtering result with accounting stats."""

    target_profile: str
    total_rows: int
    matched_rows: int
    excluded_rows: int
    rows: list[dict[str, Any]]


def filter_rows_by_industry(rows: list[dict[str, Any]], industry: str) -> IndustryFilterResult:
    """Keep rows matching target canonical profile."""
    target = resolve_industry_profile(industry).profile_key
    matched: list[dict[str, Any]] = []
    for row in rows:
        row_industry = str(row.get("industry", ""))
        row_profile = resolve_industry_profile(row_industry).profile_key
        if row_profile == target:
            matched.append(row)
    total_rows = len(rows)
    matched_rows = len(matched)
    return IndustryFilterResult(
        target_profile=target,
        total_rows=total_rows,
        matched_rows=matched_rows,
        excluded_rows=max(0, total_rows - matched_rows),
        rows=matched,
    )

