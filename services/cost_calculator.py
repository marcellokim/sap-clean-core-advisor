"""TCO and technical debt calculator (deterministic rule-based core)."""

from __future__ import annotations

from dataclasses import dataclass

from models.schemas import CustomerInput
from services.pain_point_signals import detect_pain_point_categories
from services.ruleset_loader import RulesetProfile, resolve_ruleset_profile

# Fallback reference version. Actual run uses resolved ruleset version.
RULESET_VERSION = "2026.02.14.v1"


@dataclass
class CalculationResult:
    """Deterministic calculation output."""

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
    ruleset_profile_id: str
    ruleset_profile_source: str
    calibration_quality: dict[str, float]


def _as_float(value: object, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _as_int(value: object, default: int) -> int:
    try:
        return int(float(value))
    except Exception:
        return default


def _get_config_section(profile: RulesetProfile, section: str) -> dict[str, object]:
    payload = profile.config.get(section, {})
    if isinstance(payload, dict):
        return payload
    return {}


def _get_module_weights(profile: RulesetProfile) -> dict[str, float]:
    raw = _get_config_section(profile, "module_weights")
    return {k: _as_float(v, 1.0) for k, v in raw.items() if isinstance(k, str)}


def _get_customization_score(profile: RulesetProfile) -> dict[str, float]:
    raw = _get_config_section(profile, "customization_score")
    defaults = {"low": 0.3, "medium": 0.6, "high": 1.0}
    return {
        "low": _as_float(raw.get("low"), defaults["low"]),
        "medium": _as_float(raw.get("medium"), defaults["medium"]),
        "high": _as_float(raw.get("high"), defaults["high"]),
    }


def _get_score_weights(profile: RulesetProfile) -> dict[str, float]:
    raw = _get_config_section(profile, "score_weights")
    defaults = {
        "custom_code": 0.35,
        "erp_version": 0.25,
        "database": 0.15,
        "module_complexity": 0.25,
    }
    return {
        "custom_code": _as_float(raw.get("custom_code"), defaults["custom_code"]),
        "erp_version": _as_float(raw.get("erp_version"), defaults["erp_version"]),
        "database": _as_float(raw.get("database"), defaults["database"]),
        "module_complexity": _as_float(raw.get("module_complexity"), defaults["module_complexity"]),
    }


def _get_erp_version_scores(profile: RulesetProfile) -> dict[str, float]:
    raw = _get_config_section(profile, "erp_version_scores")
    return {k: _as_float(v, 30.0) for k, v in raw.items() if isinstance(k, str)}


def _get_database_scores(profile: RulesetProfile) -> dict[str, float]:
    raw = _get_config_section(profile, "database_scores")
    return {
        "hana": _as_float(raw.get("hana"), 90.0),
        "oracle": _as_float(raw.get("oracle"), 45.0),
        "sql": _as_float(raw.get("sql"), 40.0),
        "other": _as_float(raw.get("other"), 35.0),
    }


def _get_formula_params(profile: RulesetProfile) -> dict[str, float]:
    raw = _get_config_section(profile, "formula")
    return {
        "custom_code_multiplier": _as_float(raw.get("custom_code_multiplier"), 1.5),
        "custom_program_density_penalty_rate": _as_float(raw.get("custom_program_density_penalty_rate"), 0.08),
        "custom_program_density_penalty_cap": _as_float(raw.get("custom_program_density_penalty_cap"), 10.0),
        "module_severity_multiplier": _as_float(raw.get("module_severity_multiplier"), 50.0),
        "module_count_penalty_per_module": _as_float(raw.get("module_count_penalty_per_module"), 3.0),
        "module_count_penalty_cap": _as_float(raw.get("module_count_penalty_cap"), 30.0),
        "high_custom_module_penalty": _as_float(raw.get("high_custom_module_penalty"), 4.0),
        "high_custom_module_penalty_cap": _as_float(raw.get("high_custom_module_penalty_cap"), 12.0),
        "module_complexity_empty_score": _as_float(raw.get("module_complexity_empty_score"), 80.0),
        "database_size_penalty_per_tb": _as_float(raw.get("database_size_penalty_per_tb"), 3.0),
        "database_size_penalty_cap": _as_float(raw.get("database_size_penalty_cap"), 15.0),
        "hana_size_penalty_multiplier": _as_float(raw.get("hana_size_penalty_multiplier"), 0.35),
    }


def _get_tco_params(profile: RulesetProfile) -> dict[str, float]:
    raw = _get_config_section(profile, "tco")
    return {
        "infra_cost_per_user": _as_float(raw.get("infra_cost_per_user"), 0.0003),
        "custom_maintenance_per_program": _as_float(raw.get("custom_maintenance_per_program"), 0.0005),
        "license_cost_per_user": _as_float(raw.get("license_cost_per_user"), 0.0008),
        "db_cost_per_gb": _as_float(raw.get("db_cost_per_gb"), 0.00002),
        "cloud_infra_savings_rate": _as_float(raw.get("cloud_infra_savings_rate"), 0.35),
        "clean_core_custom_savings_rate": _as_float(raw.get("clean_core_custom_savings_rate"), 0.5),
        "s4_license_change_rate": _as_float(raw.get("s4_license_change_rate"), 1.1),
    }


def _get_risk_thresholds(profile: RulesetProfile) -> dict[str, float | int]:
    raw = _get_config_section(profile, "risk_thresholds")
    return {
        "custom_ratio_medium": _as_float(raw.get("custom_ratio_medium"), 30.0),
        "custom_ratio_high": _as_float(raw.get("custom_ratio_high"), 60.0),
        "timeline_months_tight": _as_int(raw.get("timeline_months_tight"), 12),
        "timeline_custom_programs_tight": _as_int(raw.get("timeline_custom_programs_tight"), 200),
        "db_size_large_gb": _as_float(raw.get("db_size_large_gb"), 5000.0),
        "budget_ratio_medium": _as_float(raw.get("budget_ratio_medium"), 0.7),
        "budget_ratio_high": _as_float(raw.get("budget_ratio_high"), 1.0),
        "risk_level_score_high": _as_float(raw.get("risk_level_score_high"), 30.0),
        "risk_level_score_medium": _as_float(raw.get("risk_level_score_medium"), 60.0),
        "risk_factor_count_high": _as_int(raw.get("risk_factor_count_high"), 4),
        "risk_factor_count_medium": _as_int(raw.get("risk_factor_count_medium"), 2),
    }


def calculate_tech_debt_breakdown(
    inp: CustomerInput,
    ruleset_profile: RulesetProfile | None = None,
) -> dict[str, float]:
    """Calculate module-level technical debt."""
    profile = ruleset_profile or resolve_ruleset_profile(inp.industry).profile
    module_weights = _get_module_weights(profile)
    customization_score = _get_customization_score(profile)

    breakdown: dict[str, float] = {}
    for mod in inp.modules:
        weight = module_weights.get(mod.module_name, 1.0)
        severity = customization_score.get(mod.customization_level, 0.5)
        breakdown[mod.module_name] = round(weight * severity * inp.custom_code_ratio, 1)
    return breakdown


def calculate_clean_core_score(
    inp: CustomerInput,
    ruleset_profile: RulesetProfile | None = None,
) -> tuple[float, dict[str, float], list[str]]:
    """Calculate clean core score and breakdown."""
    profile = ruleset_profile or resolve_ruleset_profile(inp.industry).profile
    score_weights = _get_score_weights(profile)
    erp_scores = _get_erp_version_scores(profile)
    db_scores = _get_database_scores(profile)
    formula = _get_formula_params(profile)
    customization_score = _get_customization_score(profile)

    scores: dict[str, float] = {}
    applied_rule_ids: list[str] = []

    applied_rule_ids.append("SCORE_CUSTOM_CODE_LINEAR_1P5")
    custom_program_density = inp.num_custom_programs / max(inp.num_users / 100.0, 1.0)
    custom_program_penalty = min(
        formula["custom_program_density_penalty_cap"],
        custom_program_density * formula["custom_program_density_penalty_rate"],
    )
    applied_rule_ids.append("SCORE_CUSTOM_PROGRAM_DENSITY_V1")
    scores["custom_code"] = max(
        0.0,
        100.0
        - inp.custom_code_ratio * formula["custom_code_multiplier"]
        - custom_program_penalty,
    )

    applied_rule_ids.append("SCORE_ERP_VERSION_LOOKUP")
    scores["erp_version"] = erp_scores.get(inp.erp_version, 30.0)

    database_size_penalty = min(
        formula["database_size_penalty_cap"],
        (inp.db_size_gb / 1000.0) * formula["database_size_penalty_per_tb"],
    )
    if "HANA" in inp.db_type.upper():
        applied_rule_ids.append("SCORE_DATABASE_HANA")
        applied_rule_ids.append("SCORE_DATABASE_SIZE_MODIFIER_V1")
        scores["database"] = max(
            0.0,
            db_scores["hana"] - database_size_penalty * formula["hana_size_penalty_multiplier"],
        )
    elif "ORACLE" in inp.db_type.upper():
        applied_rule_ids.append("SCORE_DATABASE_ORACLE")
        applied_rule_ids.append("SCORE_DATABASE_SIZE_MODIFIER_V1")
        scores["database"] = max(0.0, db_scores["oracle"] - database_size_penalty)
    elif "SQL" in inp.db_type.upper():
        applied_rule_ids.append("SCORE_DATABASE_SQL")
        applied_rule_ids.append("SCORE_DATABASE_SIZE_MODIFIER_V1")
        scores["database"] = max(0.0, db_scores["sql"] - database_size_penalty)
    else:
        applied_rule_ids.append("SCORE_DATABASE_OTHER")
        applied_rule_ids.append("SCORE_DATABASE_SIZE_MODIFIER_V1")
        scores["database"] = max(0.0, db_scores["other"] - database_size_penalty)

    if inp.modules:
        applied_rule_ids.append("SCORE_MODULE_COMPLEXITY_WITH_MODULES")
        module_weights = _get_module_weights(profile)
        total_weight = sum(module_weights.get(m.module_name, 1.0) for m in inp.modules)
        weighted_severity = sum(
            module_weights.get(m.module_name, 1.0) * customization_score.get(m.customization_level, 0.5)
            for m in inp.modules
        ) / max(total_weight, 1.0)
        module_count_penalty = min(
            len(inp.modules) * formula["module_count_penalty_per_module"],
            formula["module_count_penalty_cap"],
        )
        high_custom_module_penalty = min(
            sum(1 for m in inp.modules if m.customization_level == "high")
            * formula["high_custom_module_penalty"],
            formula["high_custom_module_penalty_cap"],
        )
        applied_rule_ids.append("SCORE_MODULE_WEIGHTED_SEVERITY_V2")
        scores["module_complexity"] = max(
            0.0,
            100.0
            - weighted_severity * formula["module_severity_multiplier"]
            - module_count_penalty
            - high_custom_module_penalty,
        )
    else:
        applied_rule_ids.append("SCORE_MODULE_COMPLEXITY_EMPTY_MODULES")
        scores["module_complexity"] = formula["module_complexity_empty_score"]

    applied_rule_ids.append("SCORE_WEIGHTED_AVERAGE_V1")
    total = sum(scores[k] * score_weights[k] for k in score_weights)
    final_score = round(total, 1)

    return final_score, {k: round(v, 1) for k, v in scores.items()}, applied_rule_ids


def calculate_tco(
    inp: CustomerInput,
    ruleset_profile: RulesetProfile | None = None,
) -> tuple[float, float, float, list[str]]:
    """Calculate annual current/projection TCO and 3y savings."""
    profile = ruleset_profile or resolve_ruleset_profile(inp.industry).profile
    tco = _get_tco_params(profile)
    applied_rule_ids: list[str] = []

    applied_rule_ids.append("TCO_BASE_COST_COMPONENTS_V1")
    infra_cost = inp.num_users * tco["infra_cost_per_user"]
    db_cost = inp.db_size_gb * tco["db_cost_per_gb"]
    custom_cost = inp.num_custom_programs * tco["custom_maintenance_per_program"]
    license_cost = inp.num_users * tco["license_cost_per_user"]

    applied_rule_ids.append("TCO_CURRENT_ANNUAL_SUM")
    current_annual_tco = round(infra_cost + db_cost + custom_cost + license_cost, 2)

    applied_rule_ids.append("TCO_MIGRATED_COST_TRANSFORMATION_V1")
    projected_infra = infra_cost * (1 - tco["cloud_infra_savings_rate"]) + db_cost * 0.5
    projected_custom = custom_cost * (1 - tco["clean_core_custom_savings_rate"])
    projected_license = license_cost * tco["s4_license_change_rate"]

    applied_rule_ids.append("TCO_PROJECTED_ANNUAL_SUM")
    projected_annual_tco = round(projected_infra + projected_custom + projected_license, 2)

    applied_rule_ids.append("TCO_SAVINGS_3YR_DELTA")
    savings_3yr = round((current_annual_tco - projected_annual_tco) * 3, 2)

    return current_annual_tco, projected_annual_tco, savings_3yr, applied_rule_ids


def assess_risks(
    inp: CustomerInput,
    clean_core_score: float,
    current_annual_tco: float,
    ruleset_profile: RulesetProfile | None = None,
) -> tuple[str, list[str], list[str]]:
    """Assess migration risk level and risk factors."""
    profile = ruleset_profile or resolve_ruleset_profile(inp.industry).profile
    thresholds = _get_risk_thresholds(profile)

    risk_factors: list[str] = []
    applied_rule_ids: list[str] = []
    severity_points = 0.0

    if inp.custom_code_ratio > float(thresholds["custom_ratio_high"]):
        applied_rule_ids.append("RISK_CUSTOM_RATIO_HIGH")
        risk_factors.append(
            f"커스텀 코드 비중이 {inp.custom_code_ratio}%로 매우 높음 – 전환 시 대규모 리팩토링 필요"
        )
        severity_points += 3.0
    elif inp.custom_code_ratio > float(thresholds["custom_ratio_medium"]):
        applied_rule_ids.append("RISK_CUSTOM_RATIO_MEDIUM")
        risk_factors.append(
            f"커스텀 코드 비중 {inp.custom_code_ratio}% – 선별적 코드 정리 필요"
        )
        severity_points += 1.5

    if inp.erp_version in ("ECC 5.0", "R/3 4.7"):
        applied_rule_ids.append("RISK_ERP_EOS_IMMINENT")
        risk_factors.append(
            f"{inp.erp_version}는 지원 종료(EOS) 임박 – 즉각적인 전환 계획 필요"
        )
        severity_points += 4.0
    elif "ECC 6.0" in inp.erp_version:
        applied_rule_ids.append("RISK_BS7_MAINSTREAM_END_2027")
        applied_rule_ids.append("INFO_BS7_EXTENDED_MAINT_AVAILABLE_2030")
        risk_factors.append(
            "Business Suite 7 메인스트림 유지보수 종료(2027-12-31) 예정 – "
            "Extended Maintenance 옵션(2030-12-31) 검토 필요"
        )
        severity_points += 2.0

    if "HANA" not in inp.db_type.upper():
        applied_rule_ids.append("RISK_DB_NOT_HANA")
        risk_factors.append(
            f"현재 DB({inp.db_type})에서 SAP HANA로의 마이그레이션 필요 – 추가 비용 및 기간 발생"
        )
        severity_points += 1.5

    high_custom_modules = [
        m.module_name for m in inp.modules if m.customization_level == "high"
    ]
    if len(high_custom_modules) >= 3:
        applied_rule_ids.append("RISK_HIGH_CUSTOM_MODULES_3PLUS")
        risk_factors.append(
            f"고(High) 커스텀 모듈 {len(high_custom_modules)}개({', '.join(high_custom_modules)}) – 모듈별 단계적 전환 필수"
        )
        severity_points += 2.5
    elif high_custom_modules:
        applied_rule_ids.append("RISK_HIGH_CUSTOM_MODULES_PRESENT")
        risk_factors.append(
            f"고(High) 커스텀 모듈 {len(high_custom_modules)}개({', '.join(high_custom_modules)}) – 우선 정비 대상 지정 필요"
        )
        severity_points += 1.0

    if (
        inp.migration_timeline_months < int(thresholds["timeline_months_tight"])
        and inp.num_custom_programs > int(thresholds["timeline_custom_programs_tight"])
    ):
        applied_rule_ids.append("RISK_TIMELINE_TOO_SHORT_FOR_CUSTOM")
        risk_factors.append(
            f"커스텀 프로그램 {inp.num_custom_programs}개 대비 전환 기간 {inp.migration_timeline_months}개월은 매우 촉박"
        )
        severity_points += 2.5
    elif (
        inp.migration_timeline_months < int(thresholds["timeline_months_tight"]) + 6
        and inp.num_custom_programs > int(float(thresholds["timeline_custom_programs_tight"]) * 0.7)
    ):
        applied_rule_ids.append("RISK_TIMELINE_BUFFER_LOW")
        risk_factors.append(
            f"전환 기간 {inp.migration_timeline_months}개월 대비 커스텀 프로그램 {inp.num_custom_programs}개 – 상세 wave 계획 필요"
        )
        severity_points += 1.0

    if inp.db_size_gb > float(thresholds["db_size_large_gb"]):
        applied_rule_ids.append("RISK_DB_SIZE_LARGE")
        risk_factors.append(
            f"DB 사이즈 {inp.db_size_gb:,.0f}GB – 데이터 아카이빙 및 정리 선행 필요"
        )
        severity_points += 2.0
    elif inp.db_size_gb > float(thresholds["db_size_large_gb"]) * 0.6 and "HANA" not in inp.db_type.upper():
        applied_rule_ids.append("RISK_DB_SIZE_ELEVATED")
        risk_factors.append(
            f"DB 사이즈 {inp.db_size_gb:,.0f}GB – 대용량 전환 사전 정리 및 다운타임 최적화 검토 필요"
        )
        severity_points += 0.75

    if inp.annual_it_budget_krw > 0:
        budget_ratio = current_annual_tco / inp.annual_it_budget_krw
        if budget_ratio >= float(thresholds["budget_ratio_high"]):
            applied_rule_ids.append("RISK_BUDGET_RATIO_OVER_100")
            risk_factors.append(
                "현재 추정 TCO가 연간 IT 예산을 초과합니다 – 단계별 전환 및 비용 최적화 우선 검토 필요"
            )
            severity_points += 3.0
        elif budget_ratio >= float(thresholds["budget_ratio_medium"]):
            applied_rule_ids.append("RISK_BUDGET_RATIO_OVER_70")
            risk_factors.append(
                "현재 추정 TCO가 연간 IT 예산의 70% 이상을 점유합니다 – 운영비 구조 개선 필요"
            )
            severity_points += 1.5

    pain_point_categories = detect_pain_point_categories(inp.pain_points)
    if len(pain_point_categories) >= 3:
        applied_rule_ids.append("RISK_PAIN_POINTS_MULTI_AXIS")
        risk_factors.append(
            "주요 고충사항이 성능/업그레이드/운영 프로세스 등 복합 이슈를 시사합니다 – 사전 진단 범위 확대 필요"
        )
        severity_points += 1.5
    elif len(pain_point_categories) >= 2:
        applied_rule_ids.append("RISK_PAIN_POINTS_DUAL_AXIS")
        risk_factors.append(
            "주요 고충사항이 2개 이상 운영 축에 걸쳐 있습니다 – 핵심 pain point별 개선 트랙 분리가 필요"
        )
        severity_points += 1.0

    if clean_core_score < float(thresholds["risk_level_score_high"]):
        applied_rule_ids.append("RISK_SCORE_LT_HIGH_THRESHOLD")
        severity_points += 2.5
    elif clean_core_score < float(thresholds["risk_level_score_medium"]):
        applied_rule_ids.append("RISK_SCORE_LT_MEDIUM_THRESHOLD")
        severity_points += 1.0

    applied_rule_ids.append("RISK_LEVEL_WEIGHTED_SEVERITY_V2")
    if severity_points >= 7.0:
        applied_rule_ids.append("RISK_LEVEL_HIGH_RULE")
        risk_level = "High"
    elif severity_points >= 3.0:
        applied_rule_ids.append("RISK_LEVEL_MEDIUM_RULE")
        risk_level = "Medium"
    else:
        applied_rule_ids.append("RISK_LEVEL_LOW_RULE")
        risk_level = "Low"

    return risk_level, risk_factors, applied_rule_ids


def run_calculation(
    inp: CustomerInput,
    ruleset_profile: RulesetProfile | None = None,
) -> CalculationResult:
    """Run deterministic calculation with resolved ruleset profile."""
    profile = ruleset_profile or resolve_ruleset_profile(inp.industry).profile

    clean_core_score, score_breakdown, score_rule_ids = calculate_clean_core_score(inp, profile)
    current_tco, projected_tco, savings_3yr, tco_rule_ids = calculate_tco(inp, profile)
    risk_level, risk_factors, risk_rule_ids = assess_risks(
        inp,
        clean_core_score,
        current_tco,
        profile,
    )
    tech_debt = calculate_tech_debt_breakdown(inp, profile)
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
        ruleset_version=profile.ruleset_version or RULESET_VERSION,
        ruleset_profile_id=profile.profile_id,
        ruleset_profile_source=profile.profile_source,
        calibration_quality=profile.calibration_quality,
    )
