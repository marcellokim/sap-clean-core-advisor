"""Compatibility wrapper around the policy-driven analysis runner."""

from __future__ import annotations

import dataclasses
import os
from functools import lru_cache

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
from services.infrastructure.compat_telemetry import mark_compat_usage


@lru_cache(maxsize=1)
def _get_cached_analysis_runner():
    import streamlit as st

    @st.cache_data(ttl=3600, show_spinner=False)
    def _cached_analysis_runner(
        customer_input_dict: dict,
        lang: str = "ko",
        policy_dict: dict | None = None,
    ):
        from models.schemas import CustomerInput

        inp = CustomerInput(**customer_input_dict)

        if policy_dict:
            pol = AnalysisPolicy(**policy_dict)
        else:
            pol = AnalysisPolicy.from_env()

        return run_analysis(inp, policy=pol, lang=lang)

    return _cached_analysis_runner


def analyze_customer_input_cached(
    customer_input_dict: dict,
    lang: str = "ko",
    policy_dict: dict | None = None,
):
    """Cached wrapper for run_analysis to improve UI responsiveness.
    Takes dict inputs instead of objects because Pydantic models with varying
    run times can sometimes break Streamlit caching due to serialization.
    """
    return _get_cached_analysis_runner()(
        customer_input_dict,
        lang=lang,
        policy_dict=policy_dict,
    )


def analyze_customer_input(customer_input, lang: str = "ko", policy: AnalysisPolicy | None = None):
    """Backward-compatible entrypoint for existing callers."""

    mark_compat_usage(
        contract="services.analysis_service.analyze_customer_input",
        replacement="services.application.analysis_runner.run_analysis",
    )

    effective_policy = policy or AnalysisPolicy.from_env()

    # Bypass cache if testing
    if os.environ.get("DISABLE_CACHE") == "1":
        return run_analysis(customer_input, policy=effective_policy, lang=lang)

    return analyze_customer_input_cached(
        customer_input.model_dump(),
        lang=lang,
        policy_dict=dataclasses.asdict(effective_policy),
    )


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
