"""LLM provider interface and shared payload models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ReportPayload:
    """LLM 리포트 생성 입력 페이로드."""

    customer_info: str
    clean_core_score: float
    score_breakdown: dict[str, float]
    current_tco: float
    projected_tco: float
    savings_3yr: float
    risk_level: str
    risk_factors: list[str]
    tech_debt: dict[str, float]
    recommendations: list[str]
    rag_context: str


@dataclass(frozen=True)
class ReportSections:
    """LLM 리포트 생성 결과."""

    executive_summary: str
    detailed_report: str


class LLMProviderError(Exception):
    """LLM provider 예외."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class LLMProvider(Protocol):
    """LLM provider 인터페이스."""

    provider_name: str

    def generate_report(self, payload: ReportPayload) -> ReportSections:
        """페이로드를 받아 보고서 섹션을 생성."""
        ...
