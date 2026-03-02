"""Policy-driven analysis runner with reliability-focused orchestration."""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from uuid import uuid4

from dotenv import load_dotenv

from models.schemas import AdvisorOutput, CustomerInput
from services.cost_calculator import CalculationResult, run_calculation
from services.domain.evidence_engine import build_evidence_ledger
from services.domain.recommendation_engine import (
    RecommendationTrace,
    extract_recommendations,
    format_customer_info,
)
from services.domain.validation_engine import build_validation_warnings
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
from services.infrastructure.llm.gemini_provider import GeminiLLMProvider
from services.infrastructure.llm.glm_provider import GLMLLMProvider
from services.infrastructure.pdf.fpdf_renderer import FPDFRenderer
from services.infrastructure.rag.chroma_provider import ChromaRAGProvider
from services.llm_provider import LLMProvider, LLMProviderError, LLMUsage, ReportPayload, ReportSections
from services.rag_pipeline import RAGContextBundle
from services.ruleset_loader import resolve_ruleset_profile
from config.settings import settings

logger = logging.getLogger(__name__)
load_dotenv()

AnalysisMode = Literal["deterministic", "hybrid", "llm_only"]
RAGStatus = Literal["ok", "failed", "skipped"]
LLMStatus = Literal["ok", "fallback", "skipped"]
PDFStatus = Literal["ok", "failed"]


@dataclass(frozen=True)
class AnalysisPolicy:
    """Runtime execution policy for analysis pipeline."""

    analysis_mode: AnalysisMode = "deterministic"
    rag_enabled: bool = True
    llm_enabled: bool = True
    timeout_ms: int = 0

    @staticmethod
    def _is_true(value: str | None) -> bool:
        if value is None:
            return False
        return value.strip().lower() in {"1", "true", "t", "yes", "y", "on"}

    @classmethod
    def from_env(cls, analysis_mode: AnalysisMode | None = None) -> "AnalysisPolicy":
        mode_raw = (analysis_mode or settings.ANALYSIS_MODE).strip().lower()
        mode: AnalysisMode = "deterministic"
        if mode_raw in {"deterministic", "hybrid", "llm_only"}:
            mode = mode_raw  # type: ignore[assignment]

        return cls(
            analysis_mode=mode,
            rag_enabled=settings.RAG_ENABLE,
            llm_enabled=not settings.LLM_DISABLE,
            timeout_ms=settings.ANALYSIS_TIMEOUT_MS,
        )


@dataclass(frozen=True)
class AnalysisResult:
    """Final analysis + PDF render result."""

    output: AdvisorOutput
    pdf_bytes: bytes | None
    pdf_error_code: str | None
    pdf_error_message: str | None


_LLM_MAX_RETRIES = settings.LLM_MAX_RETRIES


def _elapsed_ms(start_ts: float) -> int:
    return max(0, int((time.perf_counter() - start_ts) * 1000))


def _timeout_hit(start_ts: float, timeout_ms: int) -> bool:
    if timeout_ms <= 0:
        return False
    return _elapsed_ms(start_ts) >= timeout_ms


def _is_true(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "t", "yes", "y", "on"}


def _select_provider_name() -> str:
    return settings.LLM_PROVIDER.strip().lower() or "gemini"


def _create_llm_provider(provider_name: str) -> LLMProvider:
    if provider_name == "gemini":
        return GeminiLLMProvider()
    if provider_name in {"glm", "glm-5", "zhipu"}:
        return GLMLLMProvider()
    raise LLMProviderError(
        ERR_PROVIDER_NOT_SUPPORTED,
        f"Provider '{provider_name}' is not supported",
    )


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


def _classify_pdf_error(exc: Exception) -> str:
    msg = str(exc).lower()
    if "not enough horizontal space" in msg:
        return ERR_PDF_LAYOUT_OVERFLOW
    if "font" in msg:
        return ERR_PDF_FONT
    return ERR_PDF_UNKNOWN


def _build_report_payload(
    inp: CustomerInput,
    calc: CalculationResult,
    recommendations: list[str],
    rag_context: str,
) -> ReportPayload:
    # 고객 정보 강화 (Pain Points 및 모듈 복잡도 추가)
    module_details = ", ".join([f"{m.module_name}({m.customization_level})" for m in inp.modules])
    customer_info = (
        f"회사: {inp.company_name}, 업종: {inp.industry}, "
        f"ERP: {inp.erp_version}, DB: {inp.db_type} ({inp.db_size_gb}GB)\n"
        f"사용 모듈 및 커스텀 심각도: {module_details}\n"
        f"주요 고충사항 (Pain Points): {inp.pain_points}"
    )

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


def _write_analysis_artifact(result: AnalysisResult) -> None:
    if not settings.ANALYSIS_ARTIFACTS_ENABLE:
        return
    root = Path(__file__).resolve().parent.parent.parent / "artifacts" / "analysis"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{result.output.analysis_id}.json"
    payload = {
        "output": result.output.model_dump(),
        "pdf_error_code": result.pdf_error_code,
        "pdf_error_message": result.pdf_error_message,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def run_analysis(
    customer_input: CustomerInput,
    policy: AnalysisPolicy | None = None,
    lang: str = "ko",
) -> AnalysisResult:
    """Run analysis under a policy with resilient stage orchestration."""
    effective_policy = policy or AnalysisPolicy.from_env()
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
    customer_info = format_customer_info(customer_input, lang=lang)
    recommendation_traces: list[RecommendationTrace] = extract_recommendations(calc, customer_input, lang=lang)
    recommendations = [trace.text for trace in recommendation_traces]
    stage_metrics_ms["calc_ms"] = _elapsed_ms(calc_start)

    rag_bundle = RAGContextBundle(context="", sources=[], chunk_count=0)
    rag_context = ""
    rag_status: RAGStatus = "skipped"
    rag_error_code: str | None = None

    should_try_rag = (
        effective_policy.analysis_mode in {"hybrid", "llm_only"}
        and effective_policy.rag_enabled
    )
    rag_start = time.perf_counter()
    if should_try_rag and not _timeout_hit(total_start, effective_policy.timeout_ms):
        try:
            rag_provider = ChromaRAGProvider()
            rag_bundle = rag_provider.get_context_bundle(
                erp_version=customer_input.erp_version,
                modules=[m.module_name for m in customer_input.modules],
                pain_points=customer_input.pain_points,
            )
            rag_context = rag_bundle.context
            rag_status = "ok"
        except Exception as exc:
            rag_status = "failed"
            rag_error_code = ERR_RAG_UNAVAILABLE
            if not settings.RAG_OFFLINE_ALLOW:
                raise
            logger.warning("RAG context unavailable, continuing without it: [%s] %s", rag_error_code, exc)
    stage_metrics_ms["rag_ms"] = _elapsed_ms(rag_start)

    payload = _build_report_payload(customer_input, calc, recommendations, rag_context)
    fallback_sections = _build_fallback_reports(customer_input, calc, recommendations)
    sections = fallback_sections

    generation_mode: Literal["llm", "fallback"] = "fallback"
    generation_provider = _select_provider_name()
    generation_error_code: str | None = ERR_LLM_DISABLED
    llm_status: LLMStatus = "skipped"
    llm_usage = LLMUsage()

    should_try_llm = (
        effective_policy.analysis_mode in {"hybrid", "llm_only"}
        and effective_policy.llm_enabled
    )
    llm_start = time.perf_counter()
    if should_try_llm and not _timeout_hit(total_start, effective_policy.timeout_ms):
        provider_name = _select_provider_name()
        generation_provider = provider_name
        try:
            provider = _create_llm_provider(provider_name)
            generation_provider = provider.provider_name
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(provider.generate_report, payload)
                if effective_policy.timeout_ms > 0:
                    sections = future.result(timeout=effective_policy.timeout_ms / 1000.0)
                else:
                    sections = future.result()
            generation_mode = "llm"
            generation_error_code = None
            llm_status = "ok"
        except LLMProviderError as exc:
            generation_mode = "fallback"
            if exc.code == ERR_PROVIDER_NOT_SUPPORTED:
                generation_error_code = ERR_PROVIDER_NOT_SUPPORTED
            else:
                generation_error_code = _normalize_llm_error_code(exc.code)
            llm_status = "fallback"
            logger.warning("LLM provider failed. Using fallback report: [%s] %s", exc.code, exc)
        except Exception as exc:  # pragma: no cover - defensive
            generation_mode = "fallback"
            generation_error_code = ERR_LLM_PROVIDER
            llm_status = "fallback"
            logger.warning("Unknown LLM provider/Timeout failure. Using fallback report: %s", exc)
    stage_metrics_ms["llm_ms"] = _elapsed_ms(llm_start)

    evidence_ledger = build_evidence_ledger(recommendation_traces, generation_mode, rag_bundle)
    validation_warnings = list(ruleset_resolution.warnings)
    validation_warnings.extend(build_validation_warnings(customer_input, calc))
    if rag_error_code and rag_status != "skipped":
        validation_warnings.append(
            f"{rag_error_code}: 컨텍스트 소스를 불러오지 못해 규칙 기반 정보 중심으로 생성했습니다."
        )
    if _timeout_hit(total_start, effective_policy.timeout_ms):
        validation_warnings.append("ANALYSIS_TIMEOUT: 타임아웃 임계치 도달로 일부 단계를 건너뛰었습니다.")

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
        analysis_mode=effective_policy.analysis_mode,
        rag_status=rag_status,
        llm_status=llm_status,
        pdf_status="failed",
        ruleset_version=calc.ruleset_version,
        ruleset_profile_id=calc.ruleset_profile_id,
        ruleset_profile_source=calc.ruleset_profile_source,
        calibration_quality=calc.calibration_quality,
        llm_usage_source=llm_usage.source,
        llm_usage_tokens={},
        llm_cost_estimate_usd=0.0,
        llm_monthly_projection_usd={},
        validation_warnings=validation_warnings,
        stage_metrics_ms=stage_metrics_ms,
        evidence_ledger=evidence_ledger,
    )

    pdf_start = time.perf_counter()
    pdf_bytes: bytes | None = None
    pdf_error_code: str | None = None
    pdf_error_message: str | None = None
    pdf_status: PDFStatus = "failed"
    try:
        renderer = FPDFRenderer()
        pdf_bytes = renderer.render(output, customer_input)
        pdf_status = "ok"
    except Exception as exc:
        pdf_error_code = _classify_pdf_error(exc)
        pdf_error_message = str(exc).strip() or None
        logger.warning("PDF generation failed: [%s] %s", pdf_error_code, exc)
    stage_metrics_ms["pdf_ms"] = _elapsed_ms(pdf_start)
    stage_metrics_ms["total_ms"] = _elapsed_ms(total_start)
    output = output.model_copy(
        update={
            "stage_metrics_ms": stage_metrics_ms,
            "pdf_status": pdf_status,
        }
    )

    result = AnalysisResult(
        output=output,
        pdf_bytes=pdf_bytes,
        pdf_error_code=pdf_error_code,
        pdf_error_message=pdf_error_message,
    )
    _write_analysis_artifact(result)

    log_payload = {
        "analysis_id": analysis_id,
        "analysis_mode": effective_policy.analysis_mode,
        "generation_mode": generation_mode,
        "generation_error_code": generation_error_code,
        "rag_status": rag_status,
        "llm_status": llm_status,
        "pdf_status": pdf_status,
        "rag_error_code": rag_error_code,
        "pdf_error_code": pdf_error_code,
        "ruleset_version": calc.ruleset_version,
        "ruleset_profile_id": calc.ruleset_profile_id,
        "ruleset_profile_source": calc.ruleset_profile_source,
        "calibration_quality": calc.calibration_quality,
        "llm_cost_estimate_usd": 0.0,
        "stage_metrics_ms": stage_metrics_ms,
        "evidence_count": len(evidence_ledger),
    }
    logger.info(json.dumps(log_payload, ensure_ascii=False))
    return result
