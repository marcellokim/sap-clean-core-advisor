"""Application service for end-to-end analysis orchestration."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from uuid import uuid4

from models.schemas import AdvisorOutput, CustomerInput
from services.cost_calculator import CalculationResult, run_calculation
from services.llm_engine import GeminiReportProvider
from services.llm_provider import LLMProviderError, ReportPayload, ReportSections
from services.pdf_generator import generate_pdf
from services.rag_pipeline import get_context_bundle_for_input

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AnalysisResult:
    """분석 + PDF 생성 결과."""

    output: AdvisorOutput
    pdf_bytes: bytes | None
    pdf_error_code: str | None
    pdf_error_message: str | None


def _is_true(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "t", "yes", "y", "on"}


def _classify_pdf_error(exc: Exception) -> str:
    msg = str(exc).lower()
    if "not enough horizontal space" in msg:
        return "layout_overflow"
    if "font" in msg:
        return "font_error"
    return "pdf_error"


def _format_customer_info(inp: CustomerInput) -> str:
    modules_str = ", ".join(f"{m.module_name}({m.customization_level})" for m in inp.modules)
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


def _build_fallback_reports(
    inp: CustomerInput,
    calc: CalculationResult,
    recommendations: list[str],
) -> ReportSections:
    top_risks = calc.risk_factors[:3] if calc.risk_factors else ["식별된 주요 리스크 없음"]
    top_recs = recommendations[:3] if recommendations else ["커스텀 코드 정리 로드맵 수립"]
    summary = (
        f"### {inp.company_name} Clean Core 사전진단 요약\n\n"
        f"- 현재 Clean Core 점수는 **{calc.clean_core_score:.1f}/100**이며, 리스크 수준은 **{calc.risk_level}**입니다.\n"
        f"- 현재 연간 TCO **{calc.current_annual_tco:.1f}억원** 대비 전환 후 **{calc.projected_tco_after_migration:.1f}억원**으로, "
        f"3년 누적 **{calc.tco_savings_3yr:.1f}억원** 변화가 예상됩니다.\n\n"
        "#### 핵심 리스크\n"
        + "\n".join(f"- {risk}" for risk in top_risks)
        + "\n\n#### 즉시 실행 Action\n"
        + "\n".join(f"- {rec}" for rec in top_recs)
    )

    detailed = (
        "## 1. 현황 분석\n"
        f"- ERP: {inp.erp_version}, DB: {inp.db_type}, 사용자: {inp.num_users:,}명, "
        f"커스텀 프로그램: {inp.num_custom_programs:,}개\n"
        f"- 커스텀 코드 비중: {inp.custom_code_ratio}%\n\n"
        "## 2. Clean Core 평가\n"
        + "\n".join(f"- {k}: {v}" for k, v in calc.score_breakdown.items())
        + "\n\n## 3. 전환 전략 및 단계\n"
        "- Phase 1: 고위험 커스텀 모듈 정리 및 대상 분류\n"
        "- Phase 2: 핵심 모듈 우선 전환(FI/CO/MM 등)\n"
        "- Phase 3: BTP 기반 확장 전환 및 운영 안정화\n\n"
        "## 4. TCO 분석\n"
        f"- 현재 연간 TCO: {calc.current_annual_tco:.1f}억원\n"
        f"- 전환 후 연간 TCO: {calc.projected_tco_after_migration:.1f}억원\n"
        f"- 3년 누적 절감/증가: {calc.tco_savings_3yr:.1f}억원\n\n"
        "## 5. 리스크 관리\n"
        + "\n".join(f"- {risk}" for risk in calc.risk_factors)
        + "\n\n## 6. 다음 단계\n"
        + "\n".join(f"- {rec}" for rec in recommendations[:5])
    )
    return ReportSections(executive_summary=summary, detailed_report=detailed)


def _extract_recommendations(calc: CalculationResult, inp: CustomerInput) -> list[str]:
    recs: list[str] = []

    if calc.clean_core_score < 30:
        recs.append(
            "Clean Core 점수가 매우 낮습니다. 커스텀 코드 대규모 정리를 최우선으로 추진하세요."
        )
    elif calc.clean_core_score < 60:
        recs.append(
            "Clean Core 개선 여지가 큽니다. 사용하지 않는 Z-code 폐기부터 시작하세요."
        )

    if "ECC" in inp.erp_version:
        recs.append(
            f"현재 {inp.erp_version}의 메인스트림 지원이 종료됩니다. "
            "RISE with SAP을 통한 S/4HANA 전환을 권고합니다."
        )

    if "HANA" not in inp.db_type.upper():
        recs.append(
            "SAP HANA로의 DB 마이그레이션을 전환 계획에 포함하세요. "
            "인메모리 처리로 분석 성능이 10-100배 향상됩니다."
        )

    if inp.custom_code_ratio > 40:
        recs.append(
            "커스텀 코드 비중이 높습니다. SAP Custom Code Migration Worklist로 "
            "Retire/Replace/Refactor 대상을 분류하세요."
        )

    if calc.tco_savings_3yr > 0:
        recs.append(
            f"Clean Core 전환 시 3년간 약 {calc.tco_savings_3yr}억원 절감이 예상됩니다. "
            "경영진 보고에 이 수치를 활용하세요."
        )

    if inp.annual_it_budget_krw > 0:
        budget_ratio = calc.current_annual_tco / inp.annual_it_budget_krw
        if budget_ratio >= 1.0:
            recs.append(
                "현재 운영 TCO가 연간 IT 예산을 초과합니다. "
                "고비용 모듈 우선 정리와 단계적 전환으로 비용 급증 리스크를 제어하세요."
            )
        elif budget_ratio >= 0.7:
            recs.append(
                "현재 운영 TCO가 연간 IT 예산의 70% 이상입니다. "
                "비핵심 커스텀 정리와 인프라 최적화 과제를 우선 실행하세요."
            )

    high_custom_modules = [m.module_name for m in inp.modules if m.customization_level == "high"]
    if high_custom_modules:
        recs.append(
            f"{', '.join(high_custom_modules)} 모듈의 핵심 커스텀은 "
            "SAP BTP Side-by-Side Extension으로 재구축을 검토하세요."
        )

    if inp.migration_timeline_months < 18 and len(inp.modules) > 5:
        recs.append(
            "모듈 수 대비 전환 기간이 촉박합니다. "
            "FI/CO 우선 전환 후 나머지를 단계적으로 진행하는 Phased Approach를 권고합니다."
        )

    return recs


def _build_report_payload(
    customer_info: str,
    calc: CalculationResult,
    recommendations: list[str],
    rag_context: str,
) -> ReportPayload:
    return ReportPayload(
        customer_info=customer_info,
        clean_core_score=calc.clean_core_score,
        score_breakdown=calc.score_breakdown,
        current_tco=calc.current_annual_tco,
        projected_tco=calc.projected_tco_after_migration,
        savings_3yr=calc.tco_savings_3yr,
        risk_level=calc.risk_level,
        risk_factors=calc.risk_factors,
        tech_debt=calc.tech_debt_breakdown,
        recommendations=recommendations,
        rag_context=rag_context,
    )


def _select_provider_name() -> str:
    return os.getenv("LLM_PROVIDER", "gemini").strip().lower() or "gemini"


def analyze_customer_input(customer_input: CustomerInput) -> AnalysisResult:
    """고객 입력 기반 분석을 수행하고 결과/부가 메타를 반환."""
    analysis_id = uuid4().hex

    calc = run_calculation(customer_input)
    customer_info = _format_customer_info(customer_input)
    recommendations = _extract_recommendations(calc, customer_input)

    rag_context = ""
    try:
        rag_bundle = get_context_bundle_for_input(
            erp_version=customer_input.erp_version,
            modules=[m.module_name for m in customer_input.modules],
            pain_points=customer_input.pain_points,
        )
        rag_context = rag_bundle.context
    except Exception as e:
        logger.warning("RAG context unavailable, continuing without it: %s", e)

    payload = _build_report_payload(customer_info, calc, recommendations, rag_context)
    fallback_sections = _build_fallback_reports(customer_input, calc, recommendations)

    generation_mode = "fallback"
    generation_provider = _select_provider_name()
    generation_error_code: str | None = "llm_disabled"
    sections = fallback_sections

    llm_disabled = _is_true(os.getenv("LLM_DISABLE", "false"))
    if not llm_disabled:
        provider_name = _select_provider_name()
        if provider_name != "gemini":
            generation_error_code = "provider_not_supported"
        else:
            provider = GeminiReportProvider()
            generation_provider = provider.provider_name
            try:
                sections = provider.generate_report(payload)
                generation_mode = "llm"
                generation_error_code = None
            except LLMProviderError as e:
                generation_mode = "fallback"
                generation_error_code = e.code
                logger.warning("LLM provider failed. Using fallback report: [%s] %s", e.code, e)
            except Exception as e:
                generation_mode = "fallback"
                generation_error_code = "provider_unknown_error"
                logger.warning("Unknown LLM provider failure. Using fallback report: %s", e)

    output = AdvisorOutput(
        clean_core_score=calc.clean_core_score,
        score_breakdown=calc.score_breakdown,
        current_annual_tco=calc.current_annual_tco,
        projected_tco_after_migration=calc.projected_tco_after_migration,
        tco_savings_3yr=calc.tco_savings_3yr,
        risk_level=calc.risk_level,
        risk_factors=calc.risk_factors,
        recommendations=recommendations,
        executive_summary=sections.executive_summary,
        detailed_report=sections.detailed_report,
        tech_debt_breakdown=calc.tech_debt_breakdown,
        generation_mode=generation_mode,
        generation_provider=generation_provider,
        generation_error_code=generation_error_code,
        analysis_id=analysis_id,
    )

    pdf_bytes: bytes | None
    pdf_error_code: str | None = None
    pdf_error_message: str | None = None
    try:
        pdf_bytes = generate_pdf(output, customer_input)
    except Exception as e:
        pdf_bytes = None
        pdf_error_code = _classify_pdf_error(e)
        pdf_error_message = str(e).strip() or None
        logger.warning("PDF generation failed: [%s] %s", pdf_error_code, e)

    return AnalysisResult(
        output=output,
        pdf_bytes=pdf_bytes,
        pdf_error_code=pdf_error_code,
        pdf_error_message=pdf_error_message,
    )
