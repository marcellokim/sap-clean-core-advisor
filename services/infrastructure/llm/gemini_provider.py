"""Infrastructure adapter for Gemini report generation."""

from __future__ import annotations

from services.llm_engine import GeminiReportProvider
from services.llm_provider import ReportPayload, ReportSections


class GeminiLLMProvider:
    """Infrastructure-facing Gemini provider adapter."""

    provider_name = "gemini"

    def __init__(self) -> None:
        self._provider = GeminiReportProvider()

    def generate_report(self, payload: ReportPayload) -> ReportSections:
        return self._provider.generate_report(payload)

