"""Infrastructure adapter for GLM report generation."""

from __future__ import annotations

import json
from urllib import error, request

from config.settings import settings
from services.error_codes import ERR_LLM_AUTH, ERR_LLM_PROVIDER, ERR_LLM_RATE_LIMIT
from services.llm_cost import estimate_usage_from_payload, normalize_usage_metadata
from services.llm_provider import LLMProviderError, ReportPayload, ReportSections
from services.infrastructure.llm.base_provider import BaseLLMProvider

DEFAULT_GLM_MODEL = "glm-5"
DEFAULT_GLM_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"

_SYSTEM_PROMPT = """\
너는 20년차 SAP Enterprise Architect다.
입력된 정량 지표를 기반으로 한국어 보고서를 작성하라.
반드시 수치와 리스크를 포함하고, 아래 두 섹션으로 구분하라.

## SECTION 1: EXECUTIVE SUMMARY
- 현재 상태 요약
- 핵심 리스크 2~3개
- 기대 효과(수치 포함)
- 즉시 실행 Action 3개

## SECTION 2: DETAILED REPORT
- 1. 현황 분석
- 2. Clean Core 평가
- 3. 전환 전략 및 단계
- 4. TCO 분석
- 5. 리스크 대응
- 6. 다음 단계

두 섹션은 반드시 "---SECTION_SEPARATOR---"로 구분하라.
"""

def _is_rate_limit_message(message: str) -> bool:
    upper = message.upper()
    return "429" in upper or "RATE LIMIT" in upper or "RESOURCE_EXHAUSTED" in upper

class GLMLLMProvider(BaseLLMProvider):
    """Infrastructure-facing GLM provider adapter."""

    provider_name = "glm"

    def __init__(self) -> None:
        super().__init__(max_retries=settings.LLM_MAX_RETRIES, base_delay=settings.LLM_BASE_DELAY_SEC)
        api_key = settings.GLM_API_KEY.strip()
        if not api_key:
            raise LLMProviderError(ERR_LLM_AUTH, "GLM_API_KEY is not configured")

        model = settings.GLM_MODEL.strip() or settings.LLM_MODEL.strip()
        self._model = model or DEFAULT_GLM_MODEL
        self._api_key = api_key
        self._base_url = settings.GLM_API_BASE_URL.rstrip("/")
        self._max_output_tokens = settings.LLM_MAX_OUTPUT_TOKENS
        self._timeout_sec = max(5, settings.LLM_HTTP_TIMEOUT_SEC)

    def _build_user_prompt(self, payload: ReportPayload) -> str:
        return (
            "[고객 정보]\n"
            f"{payload.customer_info}\n\n"
            "[정량 지표]\n"
            f"- Clean Core 점수: {payload.clean_core_score}/100\n"
            f"- 항목별 점수: {payload.score_breakdown}\n"
            f"- 현재 연간 TCO: {payload.current_tco}억원\n"
            f"- 전환 후 연간 TCO: {payload.projected_tco}억원\n"
            f"- 3년 누적 절감액: {payload.savings_3yr}억원\n"
            f"- 리스크 수준: {payload.risk_level}\n"
            f"- 리스크 요인: {payload.risk_factors}\n"
            f"- 기술 부채 분포: {payload.tech_debt}\n"
            f"- 규칙 기반 권고사항: {payload.recommendations}\n\n"
            "[RAG 컨텍스트]\n"
            f"{payload.rag_context or '(없음)'}\n"
        )

    def _invoke_generate(self, payload: ReportPayload) -> ReportSections:
        body = {
            "model": self._model,
            "temperature": 0.3,
            "max_tokens": self._max_output_tokens,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": self._build_user_prompt(payload)},
            ],
        }
        req = request.Request(
            url=f"{self._base_url}/chat/completions",
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self._timeout_sec) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
        except error.HTTPError as exc:
            err_body = exc.read().decode("utf-8", errors="replace")
            if exc.code == 429 or _is_rate_limit_message(err_body):
                raise LLMProviderError(ERR_LLM_RATE_LIMIT, err_body)
            if exc.code in {401, 403}:
                raise LLMProviderError(ERR_LLM_AUTH, err_body)
            raise LLMProviderError(ERR_LLM_PROVIDER, err_body or str(exc))
        except error.URLError as exc:
            raise LLMProviderError(ERR_LLM_PROVIDER, str(exc.reason or exc))
        except Exception as exc:  # pragma: no cover - defensive
            raise LLMProviderError(ERR_LLM_PROVIDER, str(exc))

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise LLMProviderError(ERR_LLM_PROVIDER, f"Invalid JSON response: {raw[:200]}")

        choices = parsed.get("choices", [])
        if not choices:
            raise LLMProviderError(ERR_LLM_PROVIDER, f"Missing choices in response: {raw[:300]}")

        message = choices[0].get("message", {})
        report_text = self._extract_text(message.get("content", ""))
        if not report_text.strip():
            raise LLMProviderError(ERR_LLM_PROVIDER, "Empty content from GLM response")

        usage_raw = parsed.get("usage", {})
        usage = normalize_usage_metadata(usage_raw)
        if usage.total_tokens <= 0:
            usage = estimate_usage_from_payload(payload, report_text)

        sections = self._split_sections(report_text)
        return ReportSections(
            executive_summary=sections.executive_summary,
            detailed_report=sections.detailed_report,
            usage=usage,
        )
