"""TCO 및 기술 부채 계산 로직 (Rule-based).

SAP 실무 벤치마크 기반 상수를 활용하여 Clean Core Score, TCO, 기술 부채를
규칙 기반으로 산출합니다. AI 추정에 의존하지 않습니다.
"""

from __future__ import annotations

from dataclasses import dataclass

from models.schemas import CustomerInput

# 룰셋 버전 (수동 관리)
RULESET_VERSION = "2026.02.14.v1"

# ────────────────────────────────────────────────────────────────────
# 모듈별 업계 평균 기술 부채 가중치 (SAP 실무 기반 상수)
# ────────────────────────────────────────────────────────────────────
MODULE_WEIGHTS: dict[str, float] = {
    "FI": 1.5,   # Financial Accounting – 법규 준수 요건으로 커스텀 많음
    "CO": 1.2,   # Controlling
    "MM": 1.3,   # Materials Management
    "SD": 1.4,   # Sales & Distribution – 업종별 커스텀 빈도 높음
    "PP": 1.1,   # Production Planning
    "HR": 1.6,   # Human Resources – 국가별 법규 차이로 최다 커스텀
    "PM": 0.9,   # Plant Maintenance
    "QM": 0.8,   # Quality Management
    "WM": 1.0,   # Warehouse Management
    "PS": 1.0,   # Project System
}

# 커스텀 심각도 → 숫자 점수 변환
CUSTOMIZATION_SCORE: dict[str, float] = {
    "low": 0.3,
    "medium": 0.6,
    "high": 1.0,
}

# Clean Core Score 가중치
SCORE_WEIGHTS: dict[str, float] = {
    "custom_code": 0.35,
    "erp_version": 0.25,
    "database": 0.15,
    "module_complexity": 0.25,
}

# ERP 버전별 Clean Core 근접도
ERP_VERSION_SCORES: dict[str, float] = {
    "S/4HANA 2023": 95.0,
    "S/4HANA 2021": 90.0,
    "S/4HANA 2020": 85.0,
    "S/4HANA": 90.0,
    "ECC 6.0 EHP8": 50.0,
    "ECC 6.0 EHP7": 45.0,
    "ECC 6.0": 40.0,
    "ECC 5.0": 10.0,
    "R/3 4.7": 5.0,
}

# ────────────────────────────────────────────────────────────────────
# TCO 벤치마크 상수 (단위: 억원 / 연간)
# ────────────────────────────────────────────────────────────────────
# 사용자 1인당 연간 인프라 비용 (억원)
INFRA_COST_PER_USER: float = 0.0003
# 커스텀 프로그램 1개당 연간 유지보수 비용 (억원)
CUSTOM_MAINTENANCE_PER_PROGRAM: float = 0.0005
# 라이선스 기본 비용 (사용자 수 기반, 억원/인)
LICENSE_COST_PER_USER: float = 0.0008
# 클라우드 전환 후 인프라 비용 절감률
CLOUD_INFRA_SAVINGS_RATE: float = 0.35
# Clean Core 전환 후 커스텀 유지비용 절감률
CLEAN_CORE_CUSTOM_SAVINGS_RATE: float = 0.50
# S/4HANA Cloud 라이선스 비용 변동률 (약간 증가)
S4_LICENSE_CHANGE_RATE: float = 1.10


@dataclass
class CalculationResult:
    """규칙 기반 계산 결과를 담는 데이터 클래스."""

    clean_core_score: float
    score_breakdown: dict[str, float]
    current_annual_tco: float
    projected_tco_after_migration: float
    tco_savings_3yr: float
    risk_level: str
    risk_factors: list[str]
    tech_debt_breakdown: dict[str, float]
    applied_rule_ids: list[str]
    ruleset_version: str


def calculate_tech_debt_breakdown(inp: CustomerInput) -> dict[str, float]:
    """모듈별 기술 부채를 산출.

    입력된 모듈의 커스텀 심각도 × 모듈 가중치 × 전체 커스텀 비중으로 계산.
    """
    breakdown: dict[str, float] = {}
    for mod in inp.modules:
        weight = MODULE_WEIGHTS.get(mod.module_name, 1.0)
        severity = CUSTOMIZATION_SCORE.get(mod.customization_level, 0.5)
        breakdown[mod.module_name] = round(weight * severity * inp.custom_code_ratio, 1)
    return breakdown


def calculate_clean_core_score(inp: CustomerInput) -> tuple[float, dict[str, float], list[str]]:
    """Clean Core Score(0-100)를 산출하고 항목별 breakdown을 반환."""
    scores: dict[str, float] = {}
    applied_rule_ids: list[str] = []

    # 1) 커스텀 코드 점수: 비중이 낮을수록 Clean Core에 가까움
    applied_rule_ids.append("SCORE_CUSTOM_CODE_LINEAR_1P5")
    scores["custom_code"] = max(0.0, 100.0 - inp.custom_code_ratio * 1.5)

    # 2) ERP 버전 점수
    applied_rule_ids.append("SCORE_ERP_VERSION_LOOKUP")
    scores["erp_version"] = ERP_VERSION_SCORES.get(inp.erp_version, 30.0)

    # 3) 데이터베이스 점수: HANA 사용 여부
    if "HANA" in inp.db_type.upper():
        applied_rule_ids.append("SCORE_DATABASE_HANA")
        scores["database"] = 90.0
    elif "ORACLE" in inp.db_type.upper():
        applied_rule_ids.append("SCORE_DATABASE_ORACLE")
        scores["database"] = 45.0
    elif "SQL" in inp.db_type.upper():
        applied_rule_ids.append("SCORE_DATABASE_SQL")
        scores["database"] = 40.0
    else:
        applied_rule_ids.append("SCORE_DATABASE_OTHER")
        scores["database"] = 35.0

    # 4) 모듈 복잡도 점수: 사용 모듈 수와 커스텀 심각도 기반
    if inp.modules:
        applied_rule_ids.append("SCORE_MODULE_COMPLEXITY_WITH_MODULES")
        avg_severity = sum(
            CUSTOMIZATION_SCORE.get(m.customization_level, 0.5)
            for m in inp.modules
        ) / len(inp.modules)
        module_count_penalty = min(len(inp.modules) * 3, 30)
        scores["module_complexity"] = max(
            0.0, 100.0 - avg_severity * 50 - module_count_penalty
        )
    else:
        applied_rule_ids.append("SCORE_MODULE_COMPLEXITY_EMPTY_MODULES")
        scores["module_complexity"] = 80.0

    # 가중 평균으로 최종 점수 산출
    applied_rule_ids.append("SCORE_WEIGHTED_AVERAGE_V1")
    total = sum(
        scores[k] * SCORE_WEIGHTS[k] for k in SCORE_WEIGHTS
    )
    final_score = round(total, 1)

    return final_score, {k: round(v, 1) for k, v in scores.items()}, applied_rule_ids


def calculate_tco(inp: CustomerInput) -> tuple[float, float, float, list[str]]:
    """현재 TCO, 전환 후 TCO, 3년 절감액을 산출 (단위: 억원).

    Returns:
        (current_annual_tco, projected_annual_tco, savings_3yr, applied_rule_ids)
    """
    applied_rule_ids: list[str] = []

    # ── 현재 TCO 구성 요소 ──
    applied_rule_ids.append("TCO_BASE_COST_COMPONENTS_V1")
    infra_cost = inp.num_users * INFRA_COST_PER_USER
    # DB 크기에 따른 추가 인프라 비용
    db_cost = inp.db_size_gb * 0.00002
    custom_cost = inp.num_custom_programs * CUSTOM_MAINTENANCE_PER_PROGRAM
    license_cost = inp.num_users * LICENSE_COST_PER_USER

    applied_rule_ids.append("TCO_CURRENT_ANNUAL_SUM")
    current_annual_tco = round(infra_cost + db_cost + custom_cost + license_cost, 2)

    # ── 전환 후 TCO ──
    applied_rule_ids.append("TCO_MIGRATED_COST_TRANSFORMATION_V1")
    projected_infra = infra_cost * (1 - CLOUD_INFRA_SAVINGS_RATE) + db_cost * 0.5
    projected_custom = custom_cost * (1 - CLEAN_CORE_CUSTOM_SAVINGS_RATE)
    projected_license = license_cost * S4_LICENSE_CHANGE_RATE

    applied_rule_ids.append("TCO_PROJECTED_ANNUAL_SUM")
    projected_annual_tco = round(projected_infra + projected_custom + projected_license, 2)

    # 3년 절감액
    applied_rule_ids.append("TCO_SAVINGS_3YR_DELTA")
    savings_3yr = round((current_annual_tco - projected_annual_tco) * 3, 2)

    return current_annual_tco, projected_annual_tco, savings_3yr, applied_rule_ids


def assess_risks(
    inp: CustomerInput,
    clean_core_score: float,
    current_annual_tco: float,
) -> tuple[str, list[str], list[str]]:
    """리스크 수준과 리스크 요인 목록을 반환."""
    risk_factors: list[str] = []
    applied_rule_ids: list[str] = []

    # 커스텀 코드 비중 리스크
    if inp.custom_code_ratio > 60:
        applied_rule_ids.append("RISK_CUSTOM_RATIO_HIGH")
        risk_factors.append(
            f"커스텀 코드 비중이 {inp.custom_code_ratio}%로 매우 높음 – 전환 시 대규모 리팩토링 필요"
        )
    elif inp.custom_code_ratio > 30:
        applied_rule_ids.append("RISK_CUSTOM_RATIO_MEDIUM")
        risk_factors.append(
            f"커스텀 코드 비중 {inp.custom_code_ratio}% – 선별적 코드 정리 필요"
        )

    # ERP 버전 리스크
    if inp.erp_version in ("ECC 5.0", "R/3 4.7"):
        applied_rule_ids.append("RISK_ERP_EOS_IMMINENT")
        risk_factors.append(
            f"{inp.erp_version}는 지원 종료(EOS) 임박 – 즉각적인 전환 계획 필요"
        )
    elif "ECC 6.0" in inp.erp_version:
        applied_rule_ids.append("RISK_ECC6_EOS_2027")
        risk_factors.append(
            "ECC 6.0 메인스트림 지원 종료 – 2027년까지 전환 권고"
        )

    # DB 리스크
    if "HANA" not in inp.db_type.upper():
        applied_rule_ids.append("RISK_DB_NOT_HANA")
        risk_factors.append(
            f"현재 DB({inp.db_type})에서 SAP HANA로의 마이그레이션 필요 – 추가 비용 및 기간 발생"
        )

    # 모듈 복잡도 리스크
    high_custom_modules = [
        m.module_name for m in inp.modules if m.customization_level == "high"
    ]
    if len(high_custom_modules) >= 3:
        applied_rule_ids.append("RISK_HIGH_CUSTOM_MODULES_3PLUS")
        risk_factors.append(
            f"고(High) 커스텀 모듈 {len(high_custom_modules)}개({', '.join(high_custom_modules)}) – 모듈별 단계적 전환 필수"
        )

    # 타임라인 리스크
    if inp.migration_timeline_months < 12 and inp.num_custom_programs > 200:
        applied_rule_ids.append("RISK_TIMELINE_TOO_SHORT_FOR_CUSTOM")
        risk_factors.append(
            f"커스텀 프로그램 {inp.num_custom_programs}개 대비 전환 기간 {inp.migration_timeline_months}개월은 매우 촉박"
        )

    # DB 사이즈 리스크
    if inp.db_size_gb > 5000:
        applied_rule_ids.append("RISK_DB_SIZE_LARGE")
        risk_factors.append(
            f"DB 사이즈 {inp.db_size_gb:,.0f}GB – 데이터 아카이빙 및 정리 선행 필요"
        )

    # 예산 압박 리스크
    if inp.annual_it_budget_krw > 0:
        budget_ratio = current_annual_tco / inp.annual_it_budget_krw
        if budget_ratio >= 1.0:
            applied_rule_ids.append("RISK_BUDGET_RATIO_OVER_100")
            risk_factors.append(
                "현재 추정 TCO가 연간 IT 예산을 초과합니다 – "
                "단계별 전환 및 비용 최적화 우선 검토 필요"
            )
        elif budget_ratio >= 0.7:
            applied_rule_ids.append("RISK_BUDGET_RATIO_OVER_70")
            risk_factors.append(
                "현재 추정 TCO가 연간 IT 예산의 70% 이상을 점유합니다 – "
                "운영비 구조 개선 필요"
            )

    # 리스크 레벨 판정
    if clean_core_score < 30 or len(risk_factors) >= 4:
        applied_rule_ids.append("RISK_LEVEL_HIGH_RULE")
        risk_level = "High"
    elif clean_core_score < 60 or len(risk_factors) >= 2:
        applied_rule_ids.append("RISK_LEVEL_MEDIUM_RULE")
        risk_level = "Medium"
    else:
        applied_rule_ids.append("RISK_LEVEL_LOW_RULE")
        risk_level = "Low"

    return risk_level, risk_factors, applied_rule_ids


def run_calculation(inp: CustomerInput) -> CalculationResult:
    """모든 규칙 기반 계산을 통합 실행하고 결과를 반환."""
    clean_core_score, score_breakdown, score_rule_ids = calculate_clean_core_score(inp)
    current_tco, projected_tco, savings_3yr, tco_rule_ids = calculate_tco(inp)
    risk_level, risk_factors, risk_rule_ids = assess_risks(inp, clean_core_score, current_tco)
    tech_debt = calculate_tech_debt_breakdown(inp)
    # 순서를 보존하면서 중복 제거
    all_rule_ids = list(dict.fromkeys(score_rule_ids + tco_rule_ids + risk_rule_ids))

    return CalculationResult(
        clean_core_score=clean_core_score,
        score_breakdown=score_breakdown,
        current_annual_tco=current_tco,
        projected_tco_after_migration=projected_tco,
        tco_savings_3yr=savings_3yr,
        risk_level=risk_level,
        risk_factors=risk_factors,
        tech_debt_breakdown=tech_debt,
        applied_rule_ids=all_rule_ids,
        ruleset_version=RULESET_VERSION,
    )
