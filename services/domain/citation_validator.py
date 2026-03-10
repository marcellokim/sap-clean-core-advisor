"""Evidence ledger citation coverage validator."""

from __future__ import annotations

from dataclasses import dataclass

from models.schemas import EvidenceItem
from services.domain.verification_types import ValidationIssue


@dataclass(frozen=True)
class CitationCoverage:
    """Coverage metrics for evidence ledger citation checks."""

    total_claims: int
    with_reference_source_ids: int
    d_grade_claims: int

    @property
    def coverage_ratio(self) -> float:
        if self.total_claims <= 0:
            return 1.0
        return self.with_reference_source_ids / self.total_claims


def validate_citation_coverage(
    evidence_ledger: list[EvidenceItem],
    *,
    strict_reference_ids: bool = True,
) -> tuple[list[ValidationIssue], CitationCoverage]:
    """Validate claim citation coverage for pre-confirm handoff."""
    total_claims = len(evidence_ledger)
    with_reference = sum(1 for item in evidence_ledger if item.reference_source_ids)
    d_grade_ids = [
        item.claim_id
        for item in evidence_ledger
        if item.evidence_grade == "D"
    ]
    missing_reference_ids = [
        item.claim_id
        for item in evidence_ledger
        if not item.reference_source_ids
    ]

    issues: list[ValidationIssue] = []
    if strict_reference_ids and missing_reference_ids:
        issues.append(
            ValidationIssue(
                severity="HIGH",
                code="CITATION_MISSING_REFERENCE_SOURCE_IDS",
                message=(
                    "reference_source_ids 누락 claim: "
                    + ", ".join(missing_reference_ids[:10])
                ),
            )
        )
    if d_grade_ids:
        issues.append(
            ValidationIssue(
                severity="MEDIUM",
                code="CITATION_D_GRADE_PRESENT",
                message=(
                    "D-grade claim 존재: "
                    + ", ".join(d_grade_ids[:10])
                ),
            )
        )
    if total_claims == 0:
        issues.append(
            ValidationIssue(
                severity="HIGH",
                code="CITATION_EMPTY_LEDGER",
                message="evidence_ledger가 비어 있습니다.",
            )
        )

    metrics = CitationCoverage(
        total_claims=total_claims,
        with_reference_source_ids=with_reference,
        d_grade_claims=len(d_grade_ids),
    )
    return issues, metrics
