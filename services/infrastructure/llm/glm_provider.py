"""Infrastructure adapter for GLM report generation."""

from __future__ import annotations

import json
import re
from typing import TypeVar
from urllib import error, request

from pydantic import BaseModel

from config.settings import settings
from services.error_codes import ERR_LLM_AUTH, ERR_LLM_PROVIDER, ERR_LLM_RATE_LIMIT
from services.llm_provider import LLMProviderError, ReportPayload, ReportSections, LLMUsage
from services.infrastructure.llm.base_provider import BaseLLMProvider

DEFAULT_GLM_MODEL = "glm-5"
DEFAULT_GLM_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
StructuredModelT = TypeVar("StructuredModelT", bound=BaseModel)

_SYSTEM_PROMPT = """\
너는 20년차 SAP Enterprise Architect다.
입력된 정량 지표를 기반으로 한국어 보고서를 작성하라.
반드시 수치와 리스크를 포함하고, 아래 두 섹션으로 구분하라.
보고서의 기준일은 사용자 입력에 제공된 날짜를 사용하고, [귀하의 이름] 같은 플레이스홀더는 절대 쓰지 마라.

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


def _extract_json_payload(text: str) -> dict[str, object]:
    stripped = text.strip()
    fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", stripped, re.DOTALL | re.IGNORECASE)
    if fenced:
        stripped = fenced.group(1).strip()

    if not stripped.startswith("{"):
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start != -1 and end != -1 and end > start:
            stripped = stripped[start:end + 1]

    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise LLMProviderError(ERR_LLM_PROVIDER, f"Invalid structured JSON response: {text[:200]}") from exc
    if not isinstance(parsed, dict):
        raise LLMProviderError(ERR_LLM_PROVIDER, "Structured response must be a JSON object")
    return parsed


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

    def _post_chat_completion(
        self,
        *,
        messages: list[dict[str, str]],
        max_tokens: int | None = None,
        temperature: float = 0.3,
    ) -> dict[str, object]:
        body = {
            "model": self._model,
            "temperature": temperature,
            "max_tokens": max_tokens or self._max_output_tokens,
            "messages": messages,
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
                raise LLMProviderError(ERR_LLM_RATE_LIMIT, err_body) from exc
            if exc.code in {401, 403}:
                raise LLMProviderError(ERR_LLM_AUTH, err_body) from exc
            raise LLMProviderError(ERR_LLM_PROVIDER, err_body or str(exc)) from exc
        except error.URLError as exc:
            raise LLMProviderError(ERR_LLM_PROVIDER, str(exc.reason or exc)) from exc
        except Exception as exc:  # pragma: no cover - defensive
            raise LLMProviderError(ERR_LLM_PROVIDER, str(exc)) from exc

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise LLMProviderError(ERR_LLM_PROVIDER, f"Invalid JSON response: {raw[:200]}") from exc
        if not isinstance(parsed, dict):
            raise LLMProviderError(ERR_LLM_PROVIDER, f"Unexpected JSON response: {raw[:200]}")
        return parsed

    @staticmethod
    def _message_content(parsed: dict[str, object]) -> object:
        choices = parsed.get("choices", [])
        if not choices:
            raise LLMProviderError(ERR_LLM_PROVIDER, f"Missing choices in response: {str(parsed)[:300]}")
        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise LLMProviderError(ERR_LLM_PROVIDER, f"Invalid choice in response: {str(parsed)[:300]}")
        message = first_choice.get("message", {})
        if not isinstance(message, dict):
            raise LLMProviderError(ERR_LLM_PROVIDER, f"Invalid message in response: {str(parsed)[:300]}")
        return message.get("content", "")

    def _build_user_prompt(self, payload: ReportPayload) -> str:
        return (
            "[리포트 작성 규칙]\n"
            f"- 보고서 기준일: {payload.analysis_date}\n"
            "- 위 기준일과 다른 임의 날짜를 쓰지 말 것\n"
            "- [귀하의 이름], [회사명] 같은 플레이스홀더를 쓰지 말 것\n\n"
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

    def generate_structured_output(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        output_model: type[StructuredModelT],
    ) -> StructuredModelT:
        """Generate a Pydantic-validated JSON object for structured app flows."""
        schema_json = json.dumps(output_model.model_json_schema(), ensure_ascii=False)
        structured_prompt = (
            f"{user_prompt}\n\n"
            "[출력 형식]\n"
            "- 반드시 JSON object만 반환하라. 마크다운 설명을 붙이지 마라.\n"
            "- 다음 JSON Schema를 만족해야 한다.\n"
            f"{schema_json}"
        )
        parsed = self._post_chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": structured_prompt},
            ],
            temperature=0.1,
        )
        content = self._extract_text(self._message_content(parsed))
        if not content.strip():
            raise LLMProviderError(ERR_LLM_PROVIDER, "Empty content from GLM response")
        payload = _extract_json_payload(content)
        return output_model.model_validate(payload)

    @staticmethod
    def _build_usage(parsed: dict[str, object], report_text: str) -> LLMUsage:
        usage_payload = parsed.get("usage")
        if isinstance(usage_payload, dict):
            prompt_tokens = int(usage_payload.get("prompt_tokens", 0) or 0)
            completion_tokens = int(usage_payload.get("completion_tokens", 0) or 0)
            total_tokens = int(usage_payload.get("total_tokens", 0) or 0)
            if total_tokens <= 0:
                total_tokens = prompt_tokens + completion_tokens
            if prompt_tokens > 0 or completion_tokens > 0 or total_tokens > 0:
                return LLMUsage(
                    prompt_tokens=max(0, prompt_tokens),
                    output_tokens=max(0, completion_tokens),
                    total_tokens=max(0, total_tokens),
                    source="provider",
                )

        estimated_output = int(len(report_text) / max(1.0, settings.LLM_TOKEN_ESTIMATE_CHAR_DIVISOR))
        if estimated_output > 0:
            return LLMUsage(
                prompt_tokens=0,
                output_tokens=estimated_output,
                total_tokens=estimated_output,
                source="estimated",
            )
        return LLMUsage()

    def _invoke_generate(self, payload: ReportPayload) -> ReportSections:
        parsed = self._post_chat_completion(
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": self._build_user_prompt(payload)},
            ],
        )
        report_text = self._extract_text(self._message_content(parsed))
        if not report_text.strip():
            raise LLMProviderError(ERR_LLM_PROVIDER, "Empty content from GLM response")

        usage = self._build_usage(parsed, report_text)

        sections = self._split_sections(report_text)
        return ReportSections(
            executive_summary=sections.executive_summary,
            detailed_report=sections.detailed_report,
            usage=usage,
        )
