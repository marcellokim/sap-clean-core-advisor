"""UI-level analysis policy helpers."""

from __future__ import annotations

from services.analysis_service import AnalysisPolicy


def get_locked_analysis_policy() -> AnalysisPolicy:
    """Return the portfolio-facing fixed policy (hybrid)."""
    return AnalysisPolicy.from_env(analysis_mode="hybrid")

