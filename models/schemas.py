"""Pydantic schemas for Input/Output definitions."""

from typing import Literal

from pydantic import BaseModel, Field


class ModuleInfo(BaseModel):
    """개별 SAP 모듈의 커스텀 심각도 정보."""

    module_name: str = Field(description="모듈명 (FI, CO, MM, SD 등)")
    customization_level: str = Field(
        description="커스텀 심각도: low / medium / high"
    )


class CustomerInput(BaseModel):
    """고객사 레거시 시스템 프로파일 입력 스키마."""

    company_name: str = Field(description="회사명")
    industry: str = Field(description="업종 (제조, 유통, 금융 등)")
    erp_version: str = Field(description="ERP 버전 (ECC 5.0, ECC 6.0, S/4HANA 등)")
    db_type: str = Field(description="DB 종류 (Oracle, HANA, SQL Server 등)")
    db_size_gb: float = Field(description="DB 사이즈 (GB)", ge=0)
    num_users: int = Field(description="사용자 수", ge=1)
    num_custom_programs: int = Field(description="Z-code / 커스텀 프로그램 수", ge=0)
    custom_code_ratio: float = Field(
        description="전체 코드 대비 커스텀 비중 (%)", ge=0, le=100
    )
    modules: list[ModuleInfo] = Field(
        description="사용 중인 모듈 + 모듈별 커스텀 심각도"
    )
    annual_it_budget_krw: float = Field(description="연간 IT 예산 (억원)", ge=0)
    pain_points: str = Field(default="", description="주요 고충사항 (자유 텍스트)")
    migration_timeline_months: int = Field(
        description="희망 전환 기간 (개월)", ge=1
    )


class EvidenceItem(BaseModel):
    """권고사항별 근거 체인 항목."""

    claim_id: str = Field(description="권고사항/주장 식별자")
    claim_text: str = Field(description="권고사항 원문")
    evidence_grade: Literal["A", "B", "C", "D"] = Field(
        description="근거 등급 (A: 입력+규칙, B: 규칙, C: 출처, D: 약함)"
    )
    input_facts: list[str] = Field(
        default_factory=list,
        description="주장과 직접 연관된 입력/계산 사실",
    )
    rule_ids: list[str] = Field(
        default_factory=list,
        description="주장에 연결된 규칙 ID 목록",
    )
    rag_sources: list[str] = Field(
        default_factory=list,
        description="주장 생성 시 참조된 RAG 출처 목록",
    )
    reference_source_ids: list[str] = Field(
        default_factory=list,
        description="규칙 ID 기반 문헌/리포트 출처 ID",
    )
    generation_mode: Literal["llm", "fallback"] = Field(
        description="생성 모드 (llm/fallback)",
    )


class AdvisorOutput(BaseModel):
    """SAP Clean Core Advisor 결과 출력 스키마."""

    # ── Clean Core 점수 ──
    clean_core_score: float = Field(description="Clean Core 점수 (0-100)")
    score_breakdown: dict[str, float] = Field(
        description="항목별 점수 (custom_code, erp_version, database, module_complexity)"
    )

    # ── TCO 분석 ──
    current_annual_tco: float = Field(description="현재 연간 TCO (억원)")
    projected_tco_after_migration: float = Field(description="전환 후 예상 연간 TCO (억원)")
    tco_savings_3yr: float = Field(description="3년 누적 절감액 (억원)")

    # ── 리스크 ──
    risk_level: str = Field(description="전체 리스크 수준: High / Medium / Low")
    risk_factors: list[str] = Field(description="주요 리스크 요인 목록")

    # ── 권고사항 ──
    recommendations: list[str] = Field(description="핵심 권고사항 목록")

    # ── 리포트 ──
    executive_summary: str = Field(description="임원 보고용 1장 요약 (Markdown)")
    detailed_report: str = Field(description="상세 분석 리포트 (Markdown)")

    # ── 기술 부채 ──
    tech_debt_breakdown: dict[str, float] = Field(
        description="모듈별 기술 부채 점수 (히트맵용)"
    )

    # ── 생성 메타데이터 ──
    generation_mode: Literal["llm", "fallback"] = Field(
        description="리포트 생성 모드: llm / fallback"
    )
    generation_provider: str | None = Field(
        default=None,
        description="리포트 생성 공급자 (예: gemini)",
    )
    generation_error_code: str | None = Field(
        default=None,
        description="LLM 실패/폴백 사유 코드",
    )
    analysis_id: str = Field(
        description="분석 추적 ID",
    )
    analysis_mode: Literal["deterministic", "hybrid", "llm_only"] = Field(
        default="deterministic",
        description="실행 모드(deterministic/hybrid/llm_only)",
    )
    rag_status: Literal["ok", "failed", "skipped"] = Field(
        default="skipped",
        description="RAG 단계 상태",
    )
    llm_status: Literal["ok", "fallback", "skipped"] = Field(
        default="skipped",
        description="LLM 단계 상태",
    )
    pdf_status: Literal["ok", "failed"] = Field(
        default="failed",
        description="PDF 생성 상태",
    )
    ruleset_version: str = Field(
        default="",
        description="규칙 엔진 버전 (예: 2026.02.14.v1)",
    )
    ruleset_profile_id: str = Field(
        default="base",
        description="적용된 룰셋 프로파일 ID",
    )
    ruleset_profile_source: Literal["base", "industry", "generated"] = Field(
        default="base",
        description="룰셋 출처(base/industry/generated)",
    )
    calibration_quality: dict[str, float] = Field(
        default_factory=dict,
        description="룰셋 보정 품질 메트릭 (예: mape_tco, risk_agreement)",
    )
    llm_usage_source: Literal["provider", "estimated", "none"] = Field(
        default="none",
        description="LLM 토큰 사용량 산출 출처(provider/estimated/none)",
    )
    llm_usage_tokens: dict[str, int] = Field(
        default_factory=dict,
        description="LLM 토큰 사용량(prompt/output/total)",
    )
    llm_cost_estimate_usd: float = Field(
        default=0.0,
        description="요청 1회 기준 LLM 비용 추정(USD)",
    )
    llm_monthly_projection_usd: dict[str, float] = Field(
        default_factory=dict,
        description="월간 요청량 기준 LLM 비용 추정(USD)",
    )
    validation_warnings: list[str] = Field(
        default_factory=list,
        description="입력/해석 품질 관련 비치명 경고",
    )
    stage_metrics_ms: dict[str, int] = Field(
        default_factory=dict,
        description="단계별 처리 시간(ms): calc/rag/llm/pdf/total",
    )
    evidence_ledger: list[EvidenceItem] = Field(
        default_factory=list,
        description="권고사항별 근거 체인",
    )


class GapAnalysisOutput(BaseModel):
    """Joule 도입 준비도 갭 분석 결과"""

    identified_gaps: list[str] = Field(
        description="미체크 항목을 기반으로 식별된 주요 준비도 결함(Gap)",
    )
    recommended_actions: list[str] = Field(
        description="식별된 Gap을 해소하기 위한 구체적인 액션 아이템",
    )
    risk_level: Literal["High", "Medium", "Low"] = Field(
        description="현재 준비 상태의 리스크 수준",
    )
    executive_summary: str = Field(
        description="임원 보고용 요약 (3~5문장)",
    )
