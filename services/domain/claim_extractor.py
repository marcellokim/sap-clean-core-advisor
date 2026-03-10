"""Claim extraction helpers for report pre-confirm validation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal


ClaimType = Literal["numeric", "date", "statement"]
ClaimSection = Literal["executive_summary", "detailed_report"]


@dataclass(frozen=True)
class ReportClaim:
    """Single extracted claim line from report text."""

    section: ClaimSection
    line_no: int
    claim_type: ClaimType
    text: str


_DATE_PATTERNS = [
    re.compile(r"\b20\d{2}-\d{2}-\d{2}\b"),
    re.compile(r"\b20\d{2}년\s*\d{1,2}월\s*\d{1,2}일\b"),
]
_NUMERIC_PATTERN = re.compile(r"\d+(?:,\d{3})*(?:\.\d+)?")


def _classify_claim(line: str) -> ClaimType | None:
    clean = line.strip()
    if not clean:
        return None
    if clean in {"---", "___"}:
        return None
    if clean.startswith("#"):
        return None

    for pattern in _DATE_PATTERNS:
        if pattern.search(clean):
            return "date"
    if _NUMERIC_PATTERN.search(clean):
        return "numeric"
    if clean.startswith(("-", "*", ">")) or clean[:3].isdigit():
        return "statement"
    return None


def extract_report_claims(
    executive_summary: str,
    detailed_report: str,
) -> list[ReportClaim]:
    """Extract candidate claims from executive/detailed report text."""
    claims: list[ReportClaim] = []
    for section_name, payload in (
        ("executive_summary", executive_summary),
        ("detailed_report", detailed_report),
    ):
        lines = payload.splitlines()
        for idx, line in enumerate(lines, start=1):
            claim_type = _classify_claim(line)
            if claim_type is None:
                continue
            claims.append(
                ReportClaim(
                    section=section_name,  # type: ignore[arg-type]
                    line_no=idx,
                    claim_type=claim_type,
                    text=line.strip(),
                )
            )
    return claims
