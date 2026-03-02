"""Infrastructure adapter for Gemini report generation."""

from __future__ import annotations

import logging
from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from config.settings import settings
from services.llm_provider import LLMUsage, ReportPayload, ReportSections
from services.infrastructure.llm.base_provider import BaseLLMProvider

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-2.5-flash"
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
너는 20년차 SAP Enterprise Architect이자 글로벌 최고 컨설턴트이며, 최종 보고서를 작성한다.
CIO와 경영진을 위한 설득력 있는 비즈니스 문서를 작성하라.
반드시 한국어로 작성하며 전문적인 컨설팅 펌의 어조(격식 있고 명확한 문체)를 유지하라.

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
경영진을 위한 1장짜리 핵심 요약. 마크다운의 인용구(>)나 강조(**)를 적극 활용하여 시각적으로 돋보이게 작성하라.
- **최종 진단 (One-line Summary)**: 현재 상태에 대한 강력한 한 줄 요약
- **핵심 비즈니스 리스크 (Key Risks)**: 고객의 '주요 고충사항(Pain Points)'과 연결된 2-3가지 위험 요소
- **재무적 기대 효과 (Expected ROI)**: 반드시 주어진 TCO와 절감액 데이터를 포함하여 서술
- **즉각적 조치 권고사항 (Immediate Actions)**: 실행 가능한 3가지 전략 조치

## SECTION 2: DETAILED REPORT
상세 분석 리포트. 논리적인 헤더와 글머리 기호를 사용하여 가독성을 극대화하라.
- 1. 비즈니스 고충 및 레거시 현황 분석 (Current Landscape & Pain Points)
- 2. Clean Core 아키텍처 평가 (Clean Core Assessment)
     * 특히 입력된 '사용 모듈 및 커스텀 심각도'를 바탕으로 기술 부채를 구체적으로 분석할 것.
- 3. RISE with SAP 전환 로드맵 (Transition Strategy)
     * BTP(Business Technology Platform)를 활용한 Side-by-Side 확장 전략을 구체적으로 제언할 것.
- 4. TCO 및 비즈니스 케이스 (Business Case)
- 5. 리스크 억제 방안 (Risk Mitigation)
- 6. 결론 및 Next Steps

EXECUTIVE SUMMARY와 DETAILED REPORT를 반드시 "---SECTION_SEPARATOR---"로 구분하라.
"""

SINGLE_PASS_SYSTEM = """\
너는 20년차 SAP Enterprise Architect이자 글로벌 최고 컨설턴트이며, SAP Clean Core 사전진단 결과를 최종 보고서 형태로 작성한다.
반드시 한국어로 작성하고, 경영진이 주목할 수 있도록 데이터와 숫자를 전면에 배치하라.
마크다운의 인용구(>)나 굵은 글씨(**)를 적극 활용하여 전문적인 보고서 양식을 갖춰라.

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
- **최종 진단**: 현재 시스템 상태에 대한 임팩트 있는 한 줄 요약
- **핵심 비즈니스 리스크**: {risk_factors} 및 고객의 '주요 고충사항(Pain Points)'을 연결한 2~3가지 리스크
- **재무적 기대 효과**: 3년 절감액 및 TCO 데이터를 포함한 ROI 요약
- **즉각적 조치 권고**: 당장 실행해야 할 3가지 Action Items

## SECTION 2: DETAILED REPORT
- 1. 비즈니스 고충 및 현황 분석 (Current State & Pain Points)
- 2. Clean Core 준수도 및 모듈별 커스텀 평가 (Clean Core Assessment)
     * 모듈 복잡도 지표를 바탕으로 왜 Clean Core 점수가 이렇게 나왔는지 설명할 것.
- 3. S/4HANA 및 BTP 기반 전환 로드맵 (Migration & BTP Strategy)
     * Side-by-Side Extensibility 등 구체적인 아키텍처 전환 방안을 제시할 것.
- 4. 비즈니스 케이스 및 TCO (Business Case & TCO)
- 5. 리스크 대응 및 Next Steps

두 섹션을 반드시 "---SECTION_SEPARATOR---"로 구분하라.
"""

def _extract_usage_map(response: Any) -> dict[str, Any]:
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
        return (text, LLMUsage())

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
        usage = LLMUsage()
        
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

        total_usage = LLMUsage()

        return ReportSections(
            executive_summary=sections.executive_summary,
            detailed_report=sections.detailed_report,
            usage=total_usage,
        )
