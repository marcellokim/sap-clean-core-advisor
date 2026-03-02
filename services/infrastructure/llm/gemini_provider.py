"""Infrastructure adapter for Gemini report generation."""

from __future__ import annotations

import logging
from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from config.settings import settings
from services.llm_cost import estimate_usage_from_inputs, estimate_usage_from_payload, normalize_usage_metadata
from services.llm_provider import LLMUsage, ReportPayload, ReportSections
from services.infrastructure.llm.base_provider import BaseLLMProvider

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-2.0-flash-lite"
DEFAULT_PIPELINE_MODE = "single"

ANALYST_SYSTEM = """\
너는 20년차 SAP Enterprise Architect이다.
지금부터 고객사의 레거시 SAP 시스템 현황을 진단한다.
기술 용어를 남발하지 말고, CIO/경영진이 이해할 수 있는 비즈니스 언어로 작성하라.
한국어로 작성하라.

다음 정보를 바탕으로 현재 시스템의 핵심 문제점을 3-5가지로 진단하라:

[고객 정보]
{customer_info}

[규칙 기반 분석 결과]
- Clean Core 점수: {clean_core_score}/100
- 항목별 점수: {score_breakdown}
- 현재 연간 TCO: {current_tco}억원
- 기술 부채 분포: {tech_debt}
- 리스크 수준: {risk_level}
- 리스크 요인: {risk_factors}

진단 결과를 다음 형식으로 작성하라:
1. 각 문제점에 대해 제목, 현황, 비즈니스 영향을 명시
2. 숫자와 데이터를 근거로 활용
3. 경영진의 의사결정을 돕는 톤으로 작성
"""

ARCHITECT_SYSTEM = """\
너는 20년차 SAP Enterprise Architect이다.
지금부터 Clean Core 전략 기반의 전환 방안을 수립한다.
한국어로 작성하라.

[현재 시스템 진단 결과]
{analysis}

[SAP 공식 가이드 참조 (RAG)]
{rag_context}

[고객 정보]
{customer_info}

다음을 포함하는 전환 전략을 수립하라:
1. 추천 전환 경로 (Greenfield / Brownfield / Bluefield) 및 근거
2. 모듈별 전환 우선순위 및 단계적 로드맵
3. 커스텀 코드 처리 전략 (Retire / Replace / Refactor / Replatform 비율 추정)
4. BTP 활용 방안 (Side-by-Side Extension 대상)
5. 예상 전환 기간 및 주요 마일스톤

SAP 공식 가이드의 내용을 근거로 활용하되, 고객의 구체적 상황에 맞게 맞춤화하라.
"""

REPORTER_SYSTEM = """\
너는 20년차 SAP Enterprise Architect이며, 최종 보고서를 작성한다.
CIO와 경영진을 위한 설득력 있는 비즈니스 문서를 작성하라.
한국어로 작성하라.

[고객 정보]
{customer_info}

[시스템 진단]
{analysis}

[전환 전략]
{architecture}

[정량적 데이터]
- Clean Core 점수: {clean_core_score}/100
- 현재 연간 TCO: {current_tco}억원
- 전환 후 예상 TCO: {projected_tco}억원
- 3년 누적 절감액: {savings_3yr}억원

두 개의 섹션을 작성하라:

## SECTION 1: EXECUTIVE SUMMARY
경영진을 위한 1장짜리 핵심 요약.
- 현재 상태 한 줄 요약
- 핵심 리스크 2-3개
- 전환 시 기대 효과 (반드시 숫자 포함)
- 즉시 실행 권고사항 (Action Items)
형식: Markdown, 간결하고 임팩트 있게.

## SECTION 2: DETAILED REPORT
상세 분석 리포트.
- 1. 현황 분석
- 2. Clean Core 평가
- 3. 전환 전략 및 로드맵
- 4. TCO 분석
- 5. 리스크 관리 방안
- 6. 결론 및 다음 단계
형식: Markdown, 구조화되고 전문적인 톤.

EXECUTIVE SUMMARY와 DETAILED REPORT를 반드시 "---SECTION_SEPARATOR---"로 구분하라.
"""

SINGLE_PASS_SYSTEM = """\
너는 20년차 SAP Enterprise Architect이며, SAP Clean Core 사전진단 결과를 최종 보고서 형태로 작성한다.
한국어로 작성하고, 숫자를 우선으로 사용하라.

[고객 정보]
{customer_info}

[정량 지표]
- Clean Core 점수: {clean_core_score}/100
- 항목별 점수: {score_breakdown}
- 현재 연간 TCO: {current_tco}억원
- 전환 후 연간 TCO: {projected_tco}억원
- 3년 누적 절감액: {savings_3yr}억원
- 리스크 수준: {risk_level}
- 리스크 요인: {risk_factors}
- 기술 부채 분포: {tech_debt}
- 규칙 기반 권고사항: {recommendations}

[SAP 공식 가이드 참조(RAG)]
{rag_context}

아래 두 섹션을 정확히 생성하라.

## SECTION 1: EXECUTIVE SUMMARY
- 현재 상태 한 줄 요약
- 핵심 리스크 2~3개
- 기대 효과(반드시 수치 포함)
- 즉시 실행 Action 3개

## SECTION 2: DETAILED REPORT
- 1. 현황 분석
- 2. Clean Core 평가
- 3. 전환 전략 및 단계
- 4. TCO 분석
- 5. 리스크 대응
- 6. 다음 단계

두 섹션을 반드시 "---SECTION_SEPARATOR---"로 구분하라.
"""

def _extract_usage_map(response: Any) -> dict[str, Any]:
    usage_candidates: list[dict[str, Any]] = []
    direct_usage = getattr(response, "usage_metadata", None)
    if isinstance(direct_usage, dict):
        usage_candidates.append(direct_usage)

    response_meta = getattr(response, "response_metadata", None)
    if isinstance(response_meta, dict):
        usage_meta = response_meta.get("usage_metadata")
        if isinstance(usage_meta, dict):
            usage_candidates.append(usage_meta)
        token_usage = response_meta.get("token_usage")
        if isinstance(token_usage, dict):
            usage_candidates.append(token_usage)

    for usage in usage_candidates:
        normalized = normalize_usage_metadata(usage)
        if normalized.total_tokens > 0:
            return {
                "prompt_tokens": normalized.prompt_tokens,
                "output_tokens": normalized.output_tokens,
                "total_tokens": normalized.total_tokens,
            }
    return {}

class GeminiLLMProvider(BaseLLMProvider):
    """Infrastructure-facing Gemini provider adapter."""

    provider_name = "gemini"

    def __init__(self) -> None:
        super().__init__(max_retries=settings.LLM_MAX_RETRIES, base_delay=settings.LLM_BASE_DELAY_SEC)
        model = settings.GEMINI_MODEL.strip() or DEFAULT_MODEL
        api_key = settings.GOOGLE_API_KEY
        max_output_tokens = settings.LLM_MAX_OUTPUT_TOKENS

        self._pipeline_mode = (
            settings.LLM_PIPELINE_MODE.strip().lower()
            or DEFAULT_PIPELINE_MODE
        )

        self._llm = ChatGoogleGenerativeAI(
            model=model,
            google_api_key=api_key,
            temperature=0.3,
            max_output_tokens=max_output_tokens,
        )

    def _invoke_text_with_usage(self, chain: Runnable, inputs: dict[str, Any]) -> tuple[str, LLMUsage]:
        # Using base class retry semantics inside chain invoke happens automatically if standard errors are raised?
        # Actually Google API clients raise their own errors, but BaseLLMProvider expects LLMProviderError.
        # So we should wrap standard execute in try-except that raises LLMProviderError, and base will catch it.
        # But wait, BaseLLMProvider wraps `_invoke_generate`, not chain.invoke.
        # So the wrapper around chain.invoke needs to catch google errors and raise LLMProviderError!
        from services.error_codes import ERR_LLM_AUTH, ERR_LLM_PROVIDER, ERR_LLM_RATE_LIMIT
        from services.llm_provider import LLMProviderError
        
        try:
            response = chain.invoke(inputs)
        except Exception as e:
            err_str = str(e).upper()
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "TOOMANYREQUESTS" in err_str or "QUOTA EXCEEDED" in err_str:
                raise LLMProviderError(ERR_LLM_RATE_LIMIT, str(e))
            elif "401" in err_str or "403" in err_str or "PERMISSION_DENIED" in err_str or "API KEY" in err_str:
                raise LLMProviderError(ERR_LLM_AUTH, str(e))
            else:
                raise LLMProviderError(ERR_LLM_PROVIDER, str(e))

        text = self._extract_text(getattr(response, "content", response))
        normalized_usage = normalize_usage_metadata(_extract_usage_map(response))
        if normalized_usage.total_tokens > 0:
            return (
                text,
                LLMUsage(
                    prompt_tokens=normalized_usage.prompt_tokens,
                    output_tokens=normalized_usage.output_tokens,
                    total_tokens=normalized_usage.total_tokens,
                    source="provider",
                ),
            )
        return (text, estimate_usage_from_inputs(inputs, text))

    def _invoke_generate(self, payload: ReportPayload) -> ReportSections:
        if self._pipeline_mode == "three_chain":
            return self._generate_three_chain(payload)
        return self._generate_single_pass(payload)

    def _generate_single_pass(self, payload: ReportPayload) -> ReportSections:
        single_prompt = ChatPromptTemplate.from_messages([
            ("system", SINGLE_PASS_SYSTEM),
            ("human", "위 정보를 종합하여 최종 보고서를 작성해 주세요."),
        ])
        chain = single_prompt | self._llm
        inputs = {
            "customer_info": payload.customer_info,
            "clean_core_score": payload.clean_core_score,
            "score_breakdown": payload.score_breakdown,
            "current_tco": payload.current_tco,
            "projected_tco": payload.projected_tco,
            "savings_3yr": payload.savings_3yr,
            "risk_level": payload.risk_level,
            "risk_factors": "\n".join(f"- {r}" for r in payload.risk_factors),
            "tech_debt": payload.tech_debt,
            "recommendations": "\n".join(f"- {r}" for r in payload.recommendations),
            "rag_context": payload.rag_context,
        }
        report, usage = self._invoke_text_with_usage(chain, inputs)
        sections = self._split_sections(report)
        if usage.total_tokens <= 0:
            usage = estimate_usage_from_payload(payload, report)
        
        return ReportSections(
            executive_summary=sections.executive_summary,
            detailed_report=sections.detailed_report,
            usage=usage,
        )

    def _generate_three_chain(self, payload: ReportPayload) -> ReportSections:
        import time
        analyst_prompt = ChatPromptTemplate.from_messages([
            ("system", ANALYST_SYSTEM),
            ("human", "위 정보를 바탕으로 현재 시스템의 핵심 문제점을 진단해 주세요."),
        ])
        analyst_chain = analyst_prompt | self._llm
        analysis_inputs = {
            "customer_info": payload.customer_info,
            "clean_core_score": payload.clean_core_score,
            "score_breakdown": payload.score_breakdown,
            "current_tco": payload.current_tco,
            "tech_debt": payload.tech_debt,
            "risk_level": payload.risk_level,
            "risk_factors": "\n".join(f"- {r}" for r in payload.risk_factors),
        }
        analysis, usage_analyst = self._invoke_text_with_usage(analyst_chain, analysis_inputs)

        time.sleep(2)

        architect_prompt = ChatPromptTemplate.from_messages([
            ("system", ARCHITECT_SYSTEM),
            ("human", "위 진단 결과와 SAP 공식 가이드를 참고하여 전환 전략을 수립해 주세요."),
        ])
        architect_chain = architect_prompt | self._llm
        architecture_inputs = {
            "analysis": analysis,
            "rag_context": payload.rag_context,
            "customer_info": payload.customer_info,
        }
        architecture, usage_architect = self._invoke_text_with_usage(
            architect_chain,
            architecture_inputs,
        )

        time.sleep(2)

        reporter_prompt = ChatPromptTemplate.from_messages([
            ("system", REPORTER_SYSTEM),
            ("human", "위 모든 분석을 종합하여 Executive Summary와 상세 리포트를 작성해 주세요."),
        ])
        reporter_chain = reporter_prompt | self._llm
        report_inputs = {
            "customer_info": payload.customer_info,
            "analysis": analysis,
            "architecture": architecture,
            "clean_core_score": payload.clean_core_score,
            "current_tco": payload.current_tco,
            "projected_tco": payload.projected_tco,
            "savings_3yr": payload.savings_3yr,
        }
        report, usage_reporter = self._invoke_text_with_usage(reporter_chain, report_inputs)
        sections = self._split_sections(report)

        total_usage = LLMUsage(
            prompt_tokens=(
                usage_analyst.prompt_tokens
                + usage_architect.prompt_tokens
                + usage_reporter.prompt_tokens
            ),
            output_tokens=(
                usage_analyst.output_tokens
                + usage_architect.output_tokens
                + usage_reporter.output_tokens
            ),
            total_tokens=(
                usage_analyst.total_tokens
                + usage_architect.total_tokens
                + usage_reporter.total_tokens
            ),
            source=(
                "provider"
                if all(u.source == "provider" for u in (usage_analyst, usage_architect, usage_reporter))
                else "estimated"
            ),
        )
        if total_usage.total_tokens <= 0:
            total_usage = estimate_usage_from_payload(payload, report)

        return ReportSections(
            executive_summary=sections.executive_summary,
            detailed_report=sections.detailed_report,
            usage=total_usage,
        )
