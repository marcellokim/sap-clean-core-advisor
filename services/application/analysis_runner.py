"""Policy-driven analysis runner with reliability-focused orchestration."""

from __future__ import annotations

import json
import logging
import time
import concurrent.futures
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from uuid import uuid4

from dotenv import load_dotenv

from models.schemas import AdvisorOutput, CustomerInput
from services.application.report_content import (
    build_fallback_reports,
    build_report_payload,
    collect_report_quality_issues,
    enforce_detailed_template,
)
from services.application.report_preflight import render_pdf_output, run_preconfirm_validation
from services.cost_calculator import run_calculation
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
    ERR_PROVIDER_NOT_SUPPORTED,
    ERR_RAG_UNAVAILABLE,
)
from services.infrastructure.llm.gemini_provider import GeminiLLMProvider
from services.infrastructure.llm.glm_provider import GLMLLMProvider
from services.infrastructure.pdf.fpdf_renderer import FPDFRenderer  # compatibility for test patch targets
from services.infrastructure.rag.chroma_provider import ChromaRAGProvider
from services.llm_provider import LLMProvider, LLMProviderError, LLMUsage, ReportSections
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


def _elapsed_ms(start_ts: float) -> int:
    return max(0, int((time.perf_counter() - start_ts) * 1000))


def _timeout_hit(start_ts: float, timeout_ms: int) -> bool:
    if timeout_ms <= 0:
        return False
    return _elapsed_ms(start_ts) >= timeout_ms


def _remaining_timeout_sec(start_ts: float, timeout_ms: int) -> float | None:
    """Return remaining timeout budget in seconds, or None when timeout is disabled."""
    if timeout_ms <= 0:
        return None
    remaining_ms = timeout_ms - _elapsed_ms(start_ts)
    if remaining_ms <= 0:
        return 0.0
    return remaining_ms / 1000.0


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


def _usage_tokens_map(usage: LLMUsage) -> dict[str, int]:
    return {
        "prompt_tokens": max(0, int(usage.prompt_tokens)),
        "output_tokens": max(0, int(usage.output_tokens)),
        "total_tokens": max(0, int(usage.total_tokens)),
    }


def _estimate_llm_cost_usd(usage: LLMUsage) -> float:
    prompt_cost = (max(0, usage.prompt_tokens) / 1_000_000) * settings.LLM_PRICE_INPUT_PER_1M
    output_cost = (max(0, usage.output_tokens) / 1_000_000) * settings.LLM_PRICE_OUTPUT_PER_1M
    return round(prompt_cost + output_cost, 8)


def _monthly_llm_projection_usd(cost_per_request_usd: float) -> dict[str, float]:
    monthly_requests = max(0.0, float(settings.LLM_MONTHLY_REQUESTS))
    return {
        "monthly_requests": round(monthly_requests, 2),
        "estimated_usd": round(cost_per_request_usd * monthly_requests, 4),
    }


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

    payload = build_report_payload(customer_input, calc, recommendations, rag_context)
    fallback_sections = build_fallback_reports(customer_input, calc, recommendations)
    sections = fallback_sections

    generation_mode: Literal["llm", "fallback"] = "fallback"
    generation_provider = _select_provider_name()
    generation_error_code: str | None = ERR_LLM_DISABLED
    llm_status: LLMStatus = "skipped"
    llm_usage = LLMUsage()
    llm_quality_issues: list[str] = []
    llm_quality_warnings: list[str] = []
    llm_template_enforced = False

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
            max_quality_retry = 1
            for quality_attempt in range(max_quality_retry + 1):
                executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
                future = executor.submit(provider.generate_report, payload)
                try:
                    remaining_timeout = _remaining_timeout_sec(total_start, effective_policy.timeout_ms)
                    if remaining_timeout is None:
                        candidate_sections = future.result()
                    else:
                        candidate_sections = future.result(timeout=remaining_timeout)
                finally:
                    executor.shutdown(wait=False, cancel_futures=True)

                issues = collect_report_quality_issues(
                    candidate_sections,
                    payload.analysis_date,
                )
                fatal_issue_codes = {
                    "EMPTY_EXECUTIVE_SUMMARY",
                    "EMPTY_DETAILED_REPORT",
                    "DUPLICATED_SECTIONS",
                    "PLACEHOLDER_TOKEN",
                    "REPORT_DATE_MISMATCH",
                }
                fatal_issues = [code for code in issues if code in fatal_issue_codes]
                non_fatal_issues = [code for code in issues if code not in fatal_issue_codes]

                if fatal_issues:
                    llm_quality_issues = fatal_issues
                    logger.warning(
                        "LLM output contract check failed (attempt %d/%d): %s",
                        quality_attempt + 1,
                        max_quality_retry + 1,
                        ", ".join(fatal_issues),
                    )
                    if (
                        quality_attempt < max_quality_retry
                        and not _timeout_hit(total_start, effective_policy.timeout_ms)
                    ):
                        continue
                    raise LLMProviderError(
                        ERR_LLM_PROVIDER,
                        f"LLM output contract violation: {', '.join(fatal_issues)}",
                    )

                if "MISSING_DETAILED_STRUCTURE" in non_fatal_issues:
                    candidate_sections = ReportSections(
                        executive_summary=candidate_sections.executive_summary,
                        detailed_report=enforce_detailed_template(
                            candidate_sections.detailed_report,
                            fallback_sections.detailed_report,
                        ),
                        usage=candidate_sections.usage,
                    )
                    llm_template_enforced = True
                    non_fatal_issues = [
                        code for code in non_fatal_issues if code != "MISSING_DETAILED_STRUCTURE"
                    ]

                sections = candidate_sections
                llm_usage = candidate_sections.usage
                llm_quality_issues = []
                llm_quality_warnings = non_fatal_issues
                if llm_quality_warnings:
                    logger.warning(
                        "LLM output accepted with non-fatal quality warnings: %s",
                        ", ".join(llm_quality_warnings),
                    )
                generation_mode = "llm"
                generation_error_code = None
                llm_status = "ok"
                break
        except concurrent.futures.TimeoutError:
            generation_mode = "fallback"
            generation_error_code = ERR_LLM_PROVIDER
            llm_status = "fallback"
            logger.warning("LLM generation timed out. Using fallback report.")
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
    if llm_quality_issues and llm_status != "ok":
        validation_warnings.append(
            f"LLM_OUTPUT_QUALITY_FALLBACK: 형식/날짜/플레이스홀더 검증 실패({', '.join(llm_quality_issues)})로 규칙 기반 보고서를 사용했습니다."
        )
    if llm_quality_warnings and llm_status == "ok":
        validation_warnings.append(
            f"LLM_OUTPUT_FORMAT_WARNING: 상세 섹션 구조가 약해 후속 편집을 권장합니다({', '.join(llm_quality_warnings)})."
        )
    if llm_template_enforced and llm_status == "ok":
        validation_warnings.append(
            "LLM_DETAIL_TEMPLATE_ENFORCED: 상세 섹션 구조가 약해 규칙 기반 템플릿으로 보강했습니다."
        )

    llm_usage_tokens = _usage_tokens_map(llm_usage)
    llm_cost_estimate_usd = _estimate_llm_cost_usd(llm_usage)
    llm_monthly_projection_usd = _monthly_llm_projection_usd(llm_cost_estimate_usd)

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
        llm_usage_tokens=llm_usage_tokens,
        llm_cost_estimate_usd=llm_cost_estimate_usd,
        llm_monthly_projection_usd=llm_monthly_projection_usd,
        validation_warnings=validation_warnings,
        stage_metrics_ms=stage_metrics_ms,
        evidence_ledger=evidence_ledger,
    )

    output, preconfirm_issues, _citation_metrics = run_preconfirm_validation(
        output,
        payload.analysis_date,
        validation_warnings,
    )

    pdf_start = time.perf_counter()
    pdf_bytes, pdf_error_code, pdf_error_message, pdf_status = render_pdf_output(
        output,
        customer_input,
        preconfirm_issues,
    )
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
        "llm_cost_estimate_usd": llm_cost_estimate_usd,
        "llm_usage_source": llm_usage.source,
        "llm_usage_tokens": llm_usage_tokens,
        "stage_metrics_ms": stage_metrics_ms,
        "evidence_count": len(evidence_ledger),
        "preconfirm_issue_count": len(preconfirm_issues),
        "preconfirm_high_issue_count": len(
            [issue for issue in preconfirm_issues if issue.severity == "HIGH"]
        ),
    }
    logger.info(json.dumps(log_payload, ensure_ascii=False))
    return result
