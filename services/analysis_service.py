"""Application service for end-to-end analysis orchestration."""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass
from uuid import uuid4

from models.schemas import AdvisorOutput, CustomerInput, EvidenceItem
from services.cost_calculator import CalculationResult, run_calculation
from services.error_codes import (
    ERR_LLM_AUTH,
    ERR_LLM_DISABLED,
    ERR_LLM_PROVIDER,
    ERR_LLM_RATE_LIMIT,
    ERR_PDF_FONT,
    ERR_PDF_LAYOUT_OVERFLOW,
    ERR_PDF_UNKNOWN,
    ERR_PROVIDER_NOT_SUPPORTED,
    ERR_RAG_UNAVAILABLE,
)
from services.llm_engine import GeminiReportProvider
from services.llm_provider import LLMProviderError, ReportPayload, ReportSections
from services.pdf_generator import generate_pdf
from services.rag_pipeline import RAGContextBundle, get_context_bundle_for_input
from services.reference_mapper import get_reference_source_ids
from services.ruleset_loader import resolve_ruleset_profile

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AnalysisResult:
    """분석 + PDF 생성 결과."""

    output: AdvisorOutput
    pdf_bytes: bytes | None
    pdf_error_code: str | None
    pdf_error_message: str | None


@dataclass(frozen=True)
class RecommendationTrace:
    """권고사항과 근거 매핑 정보."""

    text: str
    rule_ids: list[str]
    input_facts: list[str]


def _is_true(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "t", "yes", "y", "on"}


def _elapsed_ms(start_ts: float) -> int:
    return max(0, int((time.perf_counter() - start_ts) * 1000))


def _classify_pdf_error(exc: Exception) -> str:
    msg = str(exc).lower()
    if "not enough horizontal space" in msg:
        return ERR_PDF_LAYOUT_OVERFLOW
    if "font" in msg:
        return ERR_PDF_FONT
    return ERR_PDF_UNKNOWN


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
        f"- 현재 연간 TCO **추정치** **{calc.current_annual_tco:.1f}억원** 대비 전환 후 **추정치** **{calc.projected_tco_after_migration:.1f}억원**으로, "
        f"3년 누적 **{calc.tco_savings_3yr:.1f}억원** 변화가 예상됩니다.\n\n"
        "- 본 TCO 수치는 계약/조달 조건이 아닌 의사결정용 상대 비교 추정치입니다.\n\n"
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
        f"- 현재 연간 TCO 추정치: {calc.current_annual_tco:.1f}억원\n"
        f"- 전환 후 연간 TCO 추정치: {calc.projected_tco_after_migration:.1f}억원\n"
        f"- 3년 누적 절감/증가: {calc.tco_savings_3yr:.1f}억원\n\n"
        "- 가정: 본 추정치는 계약/라이선스/조달 조건 미반영 상대 비교 수치입니다.\n\n"
        "## 5. 리스크 관리\n"
        + "\n".join(f"- {risk}" for risk in calc.risk_factors)
        + "\n\n## 6. 다음 단계\n"
        + "\n".join(f"- {rec}" for rec in recommendations[:5])
    )
    return ReportSections(executive_summary=summary, detailed_report=detailed)


def _extract_recommendations(calc: CalculationResult, inp: CustomerInput) -> list[RecommendationTrace]:
    traces: list[RecommendationTrace] = []

    def _append(text: str, rule_id: str, facts: list[str]) -> None:
        traces.append(
            RecommendationTrace(
                text=text,
                rule_ids=[rule_id],
                input_facts=[fact for fact in facts if fact],
            )
        )

    base_score_fact = f"Clean Core Score {calc.clean_core_score:.1f}/100"
    base_tco_fact = (
        f"3년 누적 절감/증가 {calc.tco_savings_3yr:.2f}억원 "
        f"(현재 {calc.current_annual_tco:.2f}억원 → 전환 후 {calc.projected_tco_after_migration:.2f}억원)"
    )
    budget_ratio = (
        calc.current_annual_tco / inp.annual_it_budget_krw
        if inp.annual_it_budget_krw > 0
        else None
    )

    if calc.clean_core_score < 30:
        _append(
            "Clean Core 점수가 매우 낮습니다. 커스텀 코드 대규모 정리를 최우선으로 추진하세요.",
            "REC_SCORE_LT_30",
            [base_score_fact, f"커스텀 코드 비중 {inp.custom_code_ratio}%"],
        )
    elif calc.clean_core_score < 60:
        _append(
            "Clean Core 개선 여지가 큽니다. 사용하지 않는 Z-code 폐기부터 시작하세요.",
            "REC_SCORE_LT_60",
            [base_score_fact, f"커스텀 프로그램 {inp.num_custom_programs:,}개"],
        )

    if "ECC" in inp.erp_version:
        _append(
            f"현재 {inp.erp_version}은 Business Suite 7 메인스트림 유지보수 종료(2027-12-31)에 해당합니다. "
            "RISE with SAP 기반 S/4HANA 전환 계획을 수립하세요.",
            "REC_BS7_MAINSTREAM_END_2027",
            [f"ERP 버전 {inp.erp_version}", "BS7 메인스트림 종료일: 2027-12-31"],
        )
        _append(
            "Extended Maintenance 옵션(2030-12-31)도 존재하지만, 비용/가치 관점에서 임시 완충책으로만 검토하세요.",
            "INFO_BS7_EXTENDED_MAINT_AVAILABLE_2030",
            ["BS7 Extended Maintenance 가능 시점: 2030-12-31"],
        )

    if "HANA" not in inp.db_type.upper():
        _append(
            "SAP HANA로의 DB 마이그레이션을 전환 계획에 포함하세요. "
            "인메모리 처리로 분석 성능이 10-100배 향상됩니다.",
            "REC_DB_TO_HANA",
            [f"현재 DB {inp.db_type}", f"DB 크기 {inp.db_size_gb:,.0f}GB"],
        )

    if inp.custom_code_ratio > 40:
        _append(
            "커스텀 코드 비중이 높습니다. SAP Custom Code Migration Worklist로 "
            "Retire/Replace/Refactor 대상을 분류하세요.",
            "REC_CUSTOM_RATIO_OVER_40",
            [f"커스텀 코드 비중 {inp.custom_code_ratio}%", f"Z-code {inp.num_custom_programs:,}개"],
        )

    if calc.tco_savings_3yr > 0:
        _append(
            f"Clean Core 전환 시 3년간 약 {calc.tco_savings_3yr}억원 절감이 예상됩니다. "
            "경영진 보고에 이 수치를 활용하세요.",
            "REC_TCO_SAVINGS_POSITIVE",
            [base_tco_fact],
        )

    if budget_ratio is not None:
        if budget_ratio >= 1.0:
            _append(
                "현재 운영 TCO가 연간 IT 예산을 초과합니다. "
                "고비용 모듈 우선 정리와 단계적 전환으로 비용 급증 리스크를 제어하세요.",
                "REC_BUDGET_RATIO_OVER_100",
                [f"TCO/예산 비율 {budget_ratio:.2f}"],
            )
        elif budget_ratio >= 0.7:
            _append(
                "현재 운영 TCO가 연간 IT 예산의 70% 이상입니다. "
                "비핵심 커스텀 정리와 인프라 최적화 과제를 우선 실행하세요.",
                "REC_BUDGET_RATIO_OVER_70",
                [f"TCO/예산 비율 {budget_ratio:.2f}"],
            )

    high_custom_modules = [m.module_name for m in inp.modules if m.customization_level == "high"]
    if high_custom_modules:
        _append(
            f"{', '.join(high_custom_modules)} 모듈의 핵심 커스텀은 "
            "SAP BTP Side-by-Side Extension으로 재구축을 검토하세요.",
            "REC_HIGH_CUSTOM_MODULE_BTP",
            [f"High 커스텀 모듈: {', '.join(high_custom_modules)}"],
        )

    if inp.migration_timeline_months < 18 and len(inp.modules) > 5:
        _append(
            "모듈 수 대비 전환 기간이 촉박합니다. "
            "FI/CO 우선 전환 후 나머지를 단계적으로 진행하는 Phased Approach를 권고합니다.",
            "REC_TIMELINE_TIGHT_PHASED",
            [f"전환 기간 {inp.migration_timeline_months}개월", f"모듈 수 {len(inp.modules)}개"],
        )

    if not traces:
        _append(
            "핵심 모듈별로 표준 프로세스 적합성(Fit-to-Standard)을 먼저 점검하고 "
            "필수 커스텀만 남기는 정리 계획을 수립하세요.",
            "REC_DEFAULT_BASELINE",
            [base_score_fact],
        )

    return traces


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


def _normalize_llm_error_code(code: str | None) -> str:
    if not code:
        return ERR_LLM_PROVIDER
    normalized = code.strip().upper()
    code_map = {
        "ERR_LLM_RATE_LIMIT": ERR_LLM_RATE_LIMIT,
        "RATE_LIMIT": ERR_LLM_RATE_LIMIT,
        "ERR_LLM_AUTH": ERR_LLM_AUTH,
        "AUTH_ERROR": ERR_LLM_AUTH,
        "ERR_LLM_PROVIDER": ERR_LLM_PROVIDER,
        "PROVIDER_ERROR": ERR_LLM_PROVIDER,
        "PROVIDER_UNKNOWN_ERROR": ERR_LLM_PROVIDER,
    }
    return code_map.get(normalized, ERR_LLM_PROVIDER)


def _extract_source_text_map(rag_context: str) -> dict[str, str]:
    source_text_map: dict[str, str] = {}
    if not rag_context.strip():
        return source_text_map

    sections = [section.strip() for section in rag_context.split("\n\n---\n\n") if section.strip()]
    for section in sections:
        lines = section.splitlines()
        if not lines:
            continue
        match = re.search(r"\[출처:\s*([^\]]+)\]", lines[0])
        if not match:
            continue
        source = match.group(1).strip()
        body = "\n".join(lines[1:]).strip().lower()
        if source and body:
            source_text_map[source] = body
    return source_text_map


def _tokenize_claim(text: str) -> list[str]:
    raw_tokens = re.findall(r"[0-9A-Za-z가-힣]{2,}", text.lower())
    stopwords = {
        "현재",
        "전환",
        "권고",
        "기반",
        "계획",
        "검토",
        "포함",
        "하세요",
        "필요",
        "및",
        "에서",
        "으로",
        "대한",
    }
    tokens: list[str] = []
    seen: set[str] = set()
    for token in raw_tokens:
        if token in stopwords:
            continue
        if token not in seen:
            seen.add(token)
            tokens.append(token)
    return tokens


def _match_rag_sources_for_claim(
    claim_text: str,
    source_text_map: dict[str, str],
    fallback_sources: list[str],
) -> list[str]:
    if not source_text_map:
        return []

    claim_tokens = _tokenize_claim(claim_text)
    if not claim_tokens:
        return []

    scored: list[tuple[str, int]] = []
    for source, source_text in source_text_map.items():
        score = sum(1 for token in claim_tokens if token in source_text)
        if score > 0:
            scored.append((source, score))

    scored.sort(key=lambda item: item[1], reverse=True)
    matched = [source for source, _ in scored[:3]]
    if matched:
        return matched

    # 매칭 실패 시에도 RAG가 있었다면 상위 출처 일부를 제공
    return list(dict.fromkeys(fallback_sources))[:3]


def _grade_evidence(input_facts: list[str], rule_ids: list[str], rag_sources: list[str]) -> str:
    if input_facts and rule_ids:
        return "A"
    if rule_ids:
        return "B"
    if rag_sources:
        return "C"
    return "D"


def _build_evidence_ledger(
    recommendation_traces: list[RecommendationTrace],
    generation_mode: str,
    rag_bundle: RAGContextBundle,
) -> list[EvidenceItem]:
    source_text_map = _extract_source_text_map(rag_bundle.context)
    fallback_sources = list(dict.fromkeys(rag_bundle.sources))
    ledger: list[EvidenceItem] = []

    for idx, trace in enumerate(recommendation_traces, start=1):
        rag_sources = _match_rag_sources_for_claim(
            claim_text=trace.text,
            source_text_map=source_text_map,
            fallback_sources=fallback_sources,
        )
        evidence_grade = _grade_evidence(trace.input_facts, trace.rule_ids, rag_sources)
        reference_source_ids = get_reference_source_ids(trace.rule_ids)
        ledger.append(
            EvidenceItem(
                claim_id=f"CLAIM_{idx:02d}",
                claim_text=trace.text,
                evidence_grade=evidence_grade,
                input_facts=trace.input_facts,
                rule_ids=trace.rule_ids,
                rag_sources=rag_sources,
                reference_source_ids=reference_source_ids,
                generation_mode=generation_mode,
            )
        )

    return ledger


def _build_validation_warnings(inp: CustomerInput, calc: CalculationResult) -> list[str]:
    warnings: list[str] = []
    module_names = [m.module_name for m in inp.modules]

    if not module_names:
        warnings.append("사용 모듈이 비어 있습니다. 모듈 정보가 없으면 기술부채/전환우선순위 정확도가 낮아집니다.")
    else:
        seen: set[str] = set()
        duplicates: set[str] = set()
        for name in module_names:
            if name in seen:
                duplicates.add(name)
            seen.add(name)
        if duplicates:
            warnings.append(
                f"중복 모듈 입력이 감지되었습니다: {', '.join(sorted(duplicates))}. 중복 제거를 권장합니다."
            )

    if inp.custom_code_ratio >= 60 and inp.num_custom_programs < 50:
        warnings.append(
            "커스텀 코드 비중이 매우 높지만 커스텀 프로그램 수가 낮습니다. 산정 기준(라인수/오브젝트수)을 확인하세요."
        )
    if inp.custom_code_ratio <= 10 and inp.num_custom_programs > 300:
        warnings.append(
            "커스텀 코드 비중이 낮은데 커스텀 프로그램 수가 매우 높습니다. 분모 정의와 집계 대상을 확인하세요."
        )

    if inp.annual_it_budget_krw > 0:
        budget_ratio = calc.current_annual_tco / inp.annual_it_budget_krw
        if budget_ratio > 2.0:
            warnings.append(
                f"현재 TCO/예산 비율이 {budget_ratio:.2f}로 매우 높습니다. 예산값 단위(억원) 입력을 재확인하세요."
            )
        elif budget_ratio < 0.01:
            warnings.append(
                f"현재 TCO/예산 비율이 {budget_ratio:.2f}로 매우 낮습니다. 예산/사용자/커스텀 입력 누락 여부를 확인하세요."
            )

    if inp.migration_timeline_months <= 6 and inp.num_custom_programs >= 200:
        warnings.append(
            "전환 기간 대비 커스텀 프로그램 수가 많습니다. 단계적 전환 계획으로 기간 가정을 보수화하세요."
        )

    return warnings


def analyze_customer_input(customer_input: CustomerInput) -> AnalysisResult:
    """고객 입력 기반 분석을 수행하고 결과/부가 메타를 반환."""
    total_start = time.perf_counter()
    analysis_id = uuid4().hex
    stage_metrics_ms: dict[str, int] = {
        "calc_ms": 0,
        "rag_ms": 0,
        "llm_ms": 0,
        "pdf_ms": 0,
        "total_ms": 0,
    }

    calc_start = time.perf_counter()
    ruleset_resolution = resolve_ruleset_profile(customer_input.industry)
    calc = run_calculation(customer_input, ruleset_profile=ruleset_resolution.profile)
    customer_info = _format_customer_info(customer_input)
    recommendation_traces = _extract_recommendations(calc, customer_input)
    recommendations = [trace.text for trace in recommendation_traces]
    stage_metrics_ms["calc_ms"] = _elapsed_ms(calc_start)

    rag_context = ""
    rag_bundle = RAGContextBundle(context="", sources=[], chunk_count=0)
    rag_error_code: str | None = None
    rag_start = time.perf_counter()
    try:
        rag_bundle = get_context_bundle_for_input(
            erp_version=customer_input.erp_version,
            modules=[m.module_name for m in customer_input.modules],
            pain_points=customer_input.pain_points,
        )
        rag_context = rag_bundle.context
    except Exception as e:
        rag_error_code = ERR_RAG_UNAVAILABLE
        logger.warning("RAG context unavailable, continuing without it: [%s] %s", rag_error_code, e)
    stage_metrics_ms["rag_ms"] = _elapsed_ms(rag_start)

    payload = _build_report_payload(customer_info, calc, recommendations, rag_context)
    fallback_sections = _build_fallback_reports(customer_input, calc, recommendations)

    generation_mode = "fallback"
    generation_provider = _select_provider_name()
    generation_error_code: str | None = ERR_LLM_DISABLED
    sections = fallback_sections

    llm_start = time.perf_counter()
    llm_disabled = _is_true(os.getenv("LLM_DISABLE", "false"))
    if not llm_disabled:
        provider_name = _select_provider_name()
        generation_provider = provider_name
        if provider_name != "gemini":
            generation_error_code = ERR_PROVIDER_NOT_SUPPORTED
        else:
            provider = GeminiReportProvider()
            generation_provider = provider.provider_name
            try:
                sections = provider.generate_report(payload)
                generation_mode = "llm"
                generation_error_code = None
            except LLMProviderError as e:
                generation_mode = "fallback"
                generation_error_code = _normalize_llm_error_code(e.code)
                logger.warning("LLM provider failed. Using fallback report: [%s] %s", e.code, e)
            except Exception as e:
                generation_mode = "fallback"
                generation_error_code = ERR_LLM_PROVIDER
                logger.warning("Unknown LLM provider failure. Using fallback report: %s", e)
    stage_metrics_ms["llm_ms"] = _elapsed_ms(llm_start)

    evidence_ledger = _build_evidence_ledger(recommendation_traces, generation_mode, rag_bundle)
    validation_warnings = list(ruleset_resolution.warnings)
    validation_warnings.extend(_build_validation_warnings(customer_input, calc))
    if rag_error_code:
        validation_warnings.append(
            f"{rag_error_code}: 컨텍스트 소스를 불러오지 못해 규칙 기반 정보 중심으로 생성했습니다."
        )

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
        ruleset_version=calc.ruleset_version,
        ruleset_profile_id=calc.ruleset_profile_id,
        ruleset_profile_source=calc.ruleset_profile_source,
        calibration_quality=calc.calibration_quality,
        validation_warnings=validation_warnings,
        stage_metrics_ms=stage_metrics_ms,
        evidence_ledger=evidence_ledger,
    )

    pdf_start = time.perf_counter()
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
    stage_metrics_ms["pdf_ms"] = _elapsed_ms(pdf_start)
    stage_metrics_ms["total_ms"] = _elapsed_ms(total_start)
    output = output.model_copy(update={"stage_metrics_ms": stage_metrics_ms})

    logger.info(
        json.dumps(
            {
                "analysis_id": analysis_id,
                "generation_mode": generation_mode,
                "generation_error_code": generation_error_code,
                "rag_error_code": rag_error_code,
                "pdf_error_code": pdf_error_code,
                "ruleset_version": calc.ruleset_version,
                "ruleset_profile_id": calc.ruleset_profile_id,
                "ruleset_profile_source": calc.ruleset_profile_source,
                "calibration_quality": calc.calibration_quality,
                "stage_metrics_ms": stage_metrics_ms,
                "evidence_count": len(evidence_ledger),
            },
            ensure_ascii=False,
        )
    )

    return AnalysisResult(
        output=output,
        pdf_bytes=pdf_bytes,
        pdf_error_code=pdf_error_code,
        pdf_error_message=pdf_error_message,
    )
