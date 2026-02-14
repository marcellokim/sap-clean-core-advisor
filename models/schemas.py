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
