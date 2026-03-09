"""Base class for LLM report providers."""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from typing import Any

from services.error_codes import ERR_LLM_RATE_LIMIT, ERR_LLM_PROVIDER
from services.llm_provider import LLMProvider, LLMProviderError, ReportPayload, ReportSections

logger = logging.getLogger(__name__)


class BaseLLMProvider(LLMProvider, ABC):
    """Abstract base class handling common LLM provider logic like retries and parsing."""

    provider_name: str

    def __init__(self, max_retries: int = 2, base_delay: int = 5):
        self._max_retries = max(0, max_retries)
        self._base_delay = max(1, base_delay)

    @abstractmethod
    def _invoke_generate(self, payload: ReportPayload) -> ReportSections:
        """Provider-specific generation logic."""
        pass

    def generate_report(self, payload: ReportPayload) -> ReportSections:
        """Generate a report with exponential backoff on rate limit errors."""
        for attempt in range(self._max_retries + 1):
            try:
                return self._invoke_generate(payload)
            except LLMProviderError as exc:
                if exc.code == ERR_LLM_RATE_LIMIT and attempt < self._max_retries:
                    delay = self._base_delay * (2 ** attempt)
                    logger.warning(
                        "Rate limit hit in %s (attempt %d/%d). Retrying in %ds...",
                        self.provider_name, attempt + 1, self._max_retries, delay
                    )
                    time.sleep(delay)
                    continue
                raise
        raise LLMProviderError(ERR_LLM_PROVIDER, "Unexpected provider failure")

    @staticmethod
    def _split_sections(report_text: str) -> ReportSections:
        """Split raw LLM output text into Executive Summary and Detailed Report."""
        import re

        normalized = report_text.replace("\r\n", "\n")
        marker = "---SECTION_SEPARATOR---"

        # 1) Exact marker or tolerant marker variant
        if marker in normalized:
            parts = normalized.split(marker, 1)
            return ReportSections(
                executive_summary=parts[0].strip(),
                detailed_report=parts[1].strip(),
            )

        marker_match = re.search(r"(?i)-{3}\s*section[_\s-]*separator\s*-{3}", normalized)
        if marker_match:
            split_index = marker_match.start()
            return ReportSections(
                executive_summary=normalized[:split_index].strip(),
                detailed_report=normalized[marker_match.end():].strip(),
            )

        # 2) Header-driven split (handles diverse markdown heading styles)
        section2_pattern = re.compile(
            r"(?im)^\s*(?:#{1,6}\s*)?(?:section\s*2\b.*|2[\)\.\:\-]?\s*detailed\s*report\b.*)$"
        )
        section2_match = section2_pattern.search(normalized)
        if section2_match:
            split_index = section2_match.start()
            return ReportSections(
                executive_summary=normalized[:split_index].strip(),
                detailed_report=normalized[split_index:].strip(),
            )

        # 3) Final fallback: split text near cutoff to avoid duplicated sections
        if len(normalized) > 240:
            cutoff = min(len(normalized), 800)
            if len(normalized) <= cutoff:
                cutoff = max(160, len(normalized) // 2)
            split_index = normalized.find("\n\n", cutoff)
            if split_index == -1:
                split_index = cutoff
            summary = normalized[:split_index].strip()
            detail = normalized[split_index:].strip()
            if summary and detail and summary != detail:
                return ReportSections(
                    executive_summary=summary,
                    detailed_report=detail,
                )

        return ReportSections(
            executive_summary=normalized.strip(),
            detailed_report=normalized.strip(),
        )

    @staticmethod
    def _extract_text(content: Any) -> str:
        """Extract text from generic provider response formats."""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            chunks: list[str] = []
            for item in content:
                if isinstance(item, str):
                    chunks.append(item)
                    continue
                if isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str):
                        chunks.append(text)
            return "\n".join(c for c in chunks if c)
        return str(content or "")
