"""Application service for Joule readiness gap analysis."""

from __future__ import annotations

import logging
from functools import lru_cache

from config.settings import settings
from models.schemas import GapAnalysisOutput
from services.domain.joule_readiness_engine import (
    GAP_ANALYSIS_SYSTEM,
    build_deterministic_gap_analysis,
    build_gap_analysis_prompt,
)

logger = logging.getLogger(__name__)


class GeminiLLMProvider:
    """Lazy Gemini provider proxy for structured Joule output."""

    def __init__(self) -> None:
        from services.infrastructure.llm.gemini_provider import GeminiLLMProvider as Impl

        self._impl = Impl()

    def generate_structured_output(self, **kwargs):
        return self._impl.generate_structured_output(**kwargs)


def _selected_provider_name() -> str:
    return settings.LLM_PROVIDER.strip().lower() or "gemini"


def _deterministic_reason(prefix: str) -> str:
    return f"{prefix} deterministic readiness analysis를 사용했습니다."


@lru_cache(maxsize=128)
def _generate_joule_gap_analysis_cached(
    checked_items: tuple[str, ...],
    unchecked_items: tuple[str, ...],
    provider_name: str,
    llm_disabled: bool,
) -> GapAnalysisOutput:
    checked = list(checked_items)
    unchecked = list(unchecked_items)

    if llm_disabled:
        return build_deterministic_gap_analysis(
            checked,
            unchecked,
            reason=_deterministic_reason("LLM이 비활성화되어"),
        )

    if provider_name != "gemini":
        return build_deterministic_gap_analysis(
            checked,
            unchecked,
            reason=_deterministic_reason(
                f"선택한 LLM provider({provider_name})는 Joule structured output 어댑터가 없어"
            ),
        )

    prompt = build_gap_analysis_prompt(checked, unchecked)
    provider = GeminiLLMProvider()

    try:
        result = provider.generate_structured_output(
            system_prompt=GAP_ANALYSIS_SYSTEM,
            user_prompt=prompt,
            output_model=GapAnalysisOutput,
        )
        return GapAnalysisOutput.model_validate(result)
    except Exception as exc:
        logger.error("Gap Analysis LLM 호출 실패: %s", exc)
        return build_deterministic_gap_analysis(
            checked,
            unchecked,
            reason="현재 AI 분석 모듈에 연결할 수 없어 상세 갭 분석을 수행하지 못했습니다.",
        )


def generate_joule_gap_analysis(
    checked_items: list[str],
    unchecked_items: list[str],
) -> GapAnalysisOutput:
    """Generate Joule gap analysis with policy-aware deterministic fallback."""
    return _generate_joule_gap_analysis_cached(
        tuple(checked_items),
        tuple(unchecked_items),
        _selected_provider_name(),
        settings.LLM_DISABLE,
    )


def _clear_cache() -> None:
    _generate_joule_gap_analysis_cached.cache_clear()


generate_joule_gap_analysis.clear = _clear_cache  # type: ignore[attr-defined]
