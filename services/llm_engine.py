"""Claude API 연동 및 LangChain 멀티에이전트 오케스트레이션.

Analyst → Architect → Reporter 3단계 LCEL 체인으로
SAP Clean Core 진단 리포트를 생성합니다.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from models.schemas import AdvisorOutput, CustomerInput
from services.cost_calculator import CalculationResult, run_calculation
from services.rag_pipeline import get_context_for_input

load_dotenv()

# ────────────────────────────────────────────────────────────────────
# LLM 초기화
# ────────────────────────────────────────────────────────────────────
_MODEL = "claude-sonnet-4-20250514"


def _get_llm() -> ChatAnthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    return ChatAnthropic(
        model=_MODEL,
        anthropic_api_key=api_key,
        temperature=0.3,
        max_tokens=4096,
    )


# ────────────────────────────────────────────────────────────────────
# 프롬프트 정의
# ────────────────────────────────────────────────────────────────────

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


# ────────────────────────────────────────────────────────────────────
# 체인 구성
# ────────────────────────────────────────────────────────────────────


def _format_customer_info(inp: CustomerInput) -> str:
    """CustomerInput을 읽기 좋은 텍스트로 변환."""
    modules_str = ", ".join(
        f"{m.module_name}({m.customization_level})" for m in inp.modules
    )
    return (
        f"회사명: {inp.company_name}\n"
        f"업종: {inp.industry}\n"
        f"ERP 버전: {inp.erp_version}\n"
        f"DB: {inp.db_type} ({inp.db_size_gb:,.0f} GB)\n"
        f"사용자 수: {inp.num_users:,}명\n"
        f"커스텀 프로그램 수: {inp.num_custom_programs:,}개\n"
        f"커스텀 코드 비중: {inp.custom_code_ratio}%\n"
        f"사용 모듈(커스텀 심각도): {modules_str}\n"
        f"연간 IT 예산: {inp.annual_it_budget_krw}억원\n"
        f"희망 전환 기간: {inp.migration_timeline_months}개월\n"
        f"주요 고충: {inp.pain_points}"
    )


def get_advice(customer_input: CustomerInput) -> AdvisorOutput:
    """고객사 정보를 바탕으로 SAP Clean Core 분석 및 조언을 생성.

    1. 규칙 기반 계산 (Score, TCO, Risk)
    2. Analyst Chain: 현재 문제점 진단
    3. Architect Chain: RAG 기반 전환 전략 수립
    4. Reporter Chain: Executive Summary + 상세 리포트 생성
    """
    llm = _get_llm()
    parser = StrOutputParser()

    # ── Step 0: 규칙 기반 계산 ──
    calc = run_calculation(customer_input)
    customer_info = _format_customer_info(customer_input)

    # ── Step 1: Analyst – 현재 문제점 진단 ──
    analyst_prompt = ChatPromptTemplate.from_messages([
        ("system", ANALYST_SYSTEM),
        ("human", "위 정보를 바탕으로 현재 시스템의 핵심 문제점을 진단해 주세요."),
    ])
    analyst_chain = analyst_prompt | llm | parser
    analysis: str = analyst_chain.invoke({
        "customer_info": customer_info,
        "clean_core_score": calc.clean_core_score,
        "score_breakdown": calc.score_breakdown,
        "current_tco": calc.current_annual_tco,
        "tech_debt": calc.tech_debt_breakdown,
        "risk_level": calc.risk_level,
        "risk_factors": "\n".join(f"- {r}" for r in calc.risk_factors),
    })

    # ── Step 2: Architect – RAG 기반 전환 전략 ──
    module_names = [m.module_name for m in customer_input.modules]
    rag_context = get_context_for_input(
        erp_version=customer_input.erp_version,
        modules=module_names,
        pain_points=customer_input.pain_points,
    )

    architect_prompt = ChatPromptTemplate.from_messages([
        ("system", ARCHITECT_SYSTEM),
        ("human", "위 진단 결과와 SAP 공식 가이드를 참고하여 전환 전략을 수립해 주세요."),
    ])
    architect_chain = architect_prompt | llm | parser
    architecture: str = architect_chain.invoke({
        "analysis": analysis,
        "rag_context": rag_context,
        "customer_info": customer_info,
    })

    # ── Step 3: Reporter – 최종 리포트 생성 ──
    reporter_prompt = ChatPromptTemplate.from_messages([
        ("system", REPORTER_SYSTEM),
        ("human", "위 모든 분석을 종합하여 Executive Summary와 상세 리포트를 작성해 주세요."),
    ])
    reporter_chain = reporter_prompt | llm | parser
    report: str = reporter_chain.invoke({
        "customer_info": customer_info,
        "analysis": analysis,
        "architecture": architecture,
        "clean_core_score": calc.clean_core_score,
        "current_tco": calc.current_annual_tco,
        "projected_tco": calc.projected_tco_after_migration,
        "savings_3yr": calc.tco_savings_3yr,
    })

    # ── 리포트 파싱 ──
    if "---SECTION_SEPARATOR---" in report:
        parts = report.split("---SECTION_SEPARATOR---", 1)
        executive_summary = parts[0].strip()
        detailed_report = parts[1].strip()
    else:
        # 구분자가 없는 경우 전체를 상세 리포트로
        executive_summary = report[:500] + "..."
        detailed_report = report

    # ── 권고사항 추출 (규칙 기반 + AI 분석 기반) ──
    recommendations = _extract_recommendations(calc, customer_input)

    return AdvisorOutput(
        clean_core_score=calc.clean_core_score,
        score_breakdown=calc.score_breakdown,
        current_annual_tco=calc.current_annual_tco,
        projected_tco_after_migration=calc.projected_tco_after_migration,
        tco_savings_3yr=calc.tco_savings_3yr,
        risk_level=calc.risk_level,
        risk_factors=calc.risk_factors,
        recommendations=recommendations,
        executive_summary=executive_summary,
        detailed_report=detailed_report,
        tech_debt_breakdown=calc.tech_debt_breakdown,
    )


def _extract_recommendations(
    calc: CalculationResult, inp: CustomerInput
) -> list[str]:
    """규칙 기반으로 핵심 권고사항을 생성."""
    recs: list[str] = []

    # Clean Core 점수 기반 권고
    if calc.clean_core_score < 30:
        recs.append(
            "Clean Core 점수가 매우 낮습니다. 커스텀 코드 대규모 정리를 최우선으로 추진하세요."
        )
    elif calc.clean_core_score < 60:
        recs.append(
            "Clean Core 개선 여지가 큽니다. 사용하지 않는 Z-code 폐기부터 시작하세요."
        )

    # ERP 버전 기반
    if "ECC" in inp.erp_version:
        recs.append(
            f"현재 {inp.erp_version}의 메인스트림 지원이 종료됩니다. "
            "RISE with SAP을 통한 S/4HANA 전환을 권고합니다."
        )

    # DB 기반
    if "HANA" not in inp.db_type.upper():
        recs.append(
            "SAP HANA로의 DB 마이그레이션을 전환 계획에 포함하세요. "
            "인메모리 처리로 분석 성능이 10-100배 향상됩니다."
        )

    # 커스텀 코드 기반
    if inp.custom_code_ratio > 40:
        recs.append(
            "커스텀 코드 비중이 높습니다. SAP Custom Code Migration Worklist로 "
            "Retire/Replace/Refactor 대상을 분류하세요."
        )

    # TCO 기반
    if calc.tco_savings_3yr > 0:
        recs.append(
            f"Clean Core 전환 시 3년간 약 {calc.tco_savings_3yr}억원 절감이 예상됩니다. "
            "경영진 보고에 이 수치를 활용하세요."
        )

    # BTP 권고
    high_custom_modules = [
        m.module_name for m in inp.modules if m.customization_level == "high"
    ]
    if high_custom_modules:
        recs.append(
            f"{', '.join(high_custom_modules)} 모듈의 핵심 커스텀은 "
            "SAP BTP Side-by-Side Extension으로 재구축을 검토하세요."
        )

    # 타임라인 권고
    if inp.migration_timeline_months < 18 and len(inp.modules) > 5:
        recs.append(
            "모듈 수 대비 전환 기간이 촉박합니다. "
            "FI/CO 우선 전환 후 나머지를 단계적으로 진행하는 Phased Approach를 권고합니다."
        )

    return recs
