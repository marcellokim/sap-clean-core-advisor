"""Compatibility wrapper around the policy-driven analysis runner."""

from __future__ import annotations

from services.application.analysis_runner import (
    AnalysisPolicy,
    AnalysisResult,
    run_analysis,
)
from services.domain.evidence_engine import build_evidence_ledger as _build_evidence_ledger
from services.domain.evidence_engine import grade_evidence as _grade_evidence
from services.domain.recommendation_engine import (
    extract_recommendations as _extract_recommendations,
)
from services.domain.validation_engine import (
    build_validation_warnings as _build_validation_warnings,
)


def analyze_customer_input(customer_input):
    """Backward-compatible entrypoint for existing callers."""
    return run_analysis(customer_input, policy=AnalysisPolicy.from_env())


__all__ = [
    "AnalysisPolicy",
    "AnalysisResult",
    "run_analysis",
    "analyze_customer_input",
    "_extract_recommendations",
    "_grade_evidence",
    "_build_evidence_ledger",
    "_build_validation_warnings",
]
