"""Deterministic recommendation extraction logic."""

from __future__ import annotations

from dataclasses import dataclass

from models.schemas import CustomerInput
from services.cost_calculator import CalculationResult


@dataclass(frozen=True)
class RecommendationTrace:
    """Recommendation text with traceable rule linkage."""

    text: str
    rule_ids: list[str]
    input_facts: list[str]


def format_customer_info(inp: CustomerInput) -> str:
    """Format customer input for report payload."""
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


def extract_recommendations(calc: CalculationResult, inp: CustomerInput) -> list[RecommendationTrace]:
    """Build deterministic recommendation traces from input + calc."""
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

