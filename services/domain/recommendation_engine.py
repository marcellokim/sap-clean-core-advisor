"""Deterministic recommendation extraction logic."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from models.schemas import CustomerInput
from services.cost_calculator import CalculationResult
from services.pain_point_signals import detect_pain_point_categories


@dataclass(frozen=True)
class RecommendationTrace:
    """Recommendation text with traceable rule linkage."""

    text: str
    rule_ids: list[str]
    input_facts: list[str]


_LOCALES_CACHE: dict[str, dict[str, str]] = {}


def _get_locales(lang: str) -> dict[str, str]:
    if lang not in _LOCALES_CACHE:
        locales_dir = Path(__file__).parent.parent.parent / "config" / "locales"
        yaml_file = locales_dir / f"{lang}.yaml"
        if not yaml_file.exists():
            # fallback to korean
            yaml_file = locales_dir / "ko.yaml"
        if yaml_file.exists():
            with yaml_file.open("r", encoding="utf-8") as f:
                _LOCALES_CACHE[lang] = yaml.safe_load(f) or {}
        else:
            _LOCALES_CACHE[lang] = {}
    return _LOCALES_CACHE[lang]


def format_customer_info(inp: CustomerInput, lang: str = "ko") -> str:
    """Format customer input for report payload."""
    locales = _get_locales(lang)
    modules_str = ", ".join(f"{m.module_name}({m.customization_level})" for m in inp.modules)
    return "\n".join([
        locales.get("INFO_COMPANY", "Company: {val}").format(val=inp.company_name),
        locales.get("INFO_INDUSTRY", "Industry: {val}").format(val=inp.industry),
        locales.get("INFO_ERP", "ERP Version: {val}").format(val=inp.erp_version),
        locales.get("INFO_DB", "DB: {type} ({size} GB)").format(type=inp.db_type, size=f"{inp.db_size_gb:,.0f}"),
        locales.get("INFO_USERS", "Users: {val:,}").format(val=inp.num_users),
        locales.get("INFO_CUSTOM_PROG", "Custom Programs: {val:,}").format(val=inp.num_custom_programs),
        locales.get("INFO_CUSTOM_RATIO", "Custom Code Ratio: {val}%").format(val=inp.custom_code_ratio),
        locales.get("INFO_MODULES", "Modules: {val}").format(val=modules_str),
        locales.get("INFO_BUDGET", "Annual IT Budget: {val}").format(val=inp.annual_it_budget_krw),
        locales.get("INFO_TIMELINE", "Desired Timeline: {val}").format(val=inp.migration_timeline_months),
        locales.get("INFO_PAIN_POINTS", "Pain Points: {val}").format(val=inp.pain_points),
    ])


def extract_recommendations(calc: CalculationResult, inp: CustomerInput, lang: str = "ko") -> list[RecommendationTrace]:
    """Build deterministic recommendation traces from input + calc."""
    locales = _get_locales(lang)
    traces: list[RecommendationTrace] = []

    def _append(msg_key: str, rule_id: str, facts: list[str], **kwargs: object) -> None:
        text_template = locales.get(msg_key, msg_key)
        traces.append(
            RecommendationTrace(
                text=text_template.format(**kwargs),
                rule_ids=[rule_id],
                input_facts=[fact for fact in facts if fact],
            )
        )

    def _fact(fact_key: str, **kwargs: object) -> str:
        return locales.get(fact_key, fact_key).format(**kwargs)

    base_score_fact = _fact("FACT_CLEAN_CORE_SCORE", score=calc.clean_core_score)
    base_tco_fact = _fact("FACT_TCO_SAVINGS", savings=calc.tco_savings_3yr, current=calc.current_annual_tco, projected=calc.projected_tco_after_migration)

    budget_ratio = (
        calc.current_annual_tco / inp.annual_it_budget_krw
        if inp.annual_it_budget_krw > 0
        else None
    )

    if calc.clean_core_score < 30:
        _append(
            "REC_SCORE_LT_30",
            "REC_SCORE_LT_30",
            [base_score_fact, _fact("FACT_CUSTOM_RATIO", ratio=inp.custom_code_ratio)],
        )
    elif calc.clean_core_score < 60:
        _append(
            "REC_SCORE_LT_60",
            "REC_SCORE_LT_60",
            [base_score_fact, _fact("FACT_CUSTOM_PROGRAMS", count=inp.num_custom_programs)],
        )

    if "ECC" in inp.erp_version:
        _append(
            "REC_BS7_MAINSTREAM_END_2027",
            "REC_BS7_MAINSTREAM_END_2027",
            [_fact("FACT_ERP_VERSION", version=inp.erp_version), _fact("FACT_BS7_MAINSTREAM")],
            erp_version=inp.erp_version,
        )
        _append(
            "INFO_BS7_EXTENDED_MAINT_AVAILABLE_2030",
            "INFO_BS7_EXTENDED_MAINT_AVAILABLE_2030",
            [_fact("FACT_BS7_EXTENDED")],
        )

    if "HANA" not in inp.db_type.upper():
        _append(
            "REC_DB_TO_HANA",
            "REC_DB_TO_HANA",
            [_fact("FACT_CURRENT_DB", db_type=inp.db_type), _fact("FACT_DB_SIZE", size=f"{inp.db_size_gb:,.0f}")],
        )

    if inp.custom_code_ratio > 40:
        _append(
            "REC_CUSTOM_RATIO_OVER_40",
            "REC_CUSTOM_RATIO_OVER_40",
            [_fact("FACT_CUSTOM_RATIO", ratio=inp.custom_code_ratio), _fact("FACT_Z_CODE", count=inp.num_custom_programs)],
        )

    if calc.tco_savings_3yr > 0:
        _append(
            "REC_TCO_SAVINGS_POSITIVE",
            "REC_TCO_SAVINGS_POSITIVE",
            [base_tco_fact],
            tco_savings_3yr=calc.tco_savings_3yr,
        )

    if budget_ratio is not None:
        if budget_ratio >= 1.0:
            _append(
                "REC_BUDGET_RATIO_OVER_100",
                "REC_BUDGET_RATIO_OVER_100",
                [_fact("FACT_TCO_BUDGET_RATIO", ratio=budget_ratio)],
            )
        elif budget_ratio >= 0.7:
            _append(
                "REC_BUDGET_RATIO_OVER_70",
                "REC_BUDGET_RATIO_OVER_70",
                [_fact("FACT_TCO_BUDGET_RATIO", ratio=budget_ratio)],
            )

    high_custom_modules = [m.module_name for m in inp.modules if m.customization_level == "high"]
    if high_custom_modules:
        _append(
            "REC_HIGH_CUSTOM_MODULE_BTP",
            "REC_HIGH_CUSTOM_MODULE_BTP",
            [_fact("FACT_HIGH_CUSTOM", modules=", ".join(high_custom_modules))],
            high_custom_modules=", ".join(high_custom_modules),
        )

    if inp.migration_timeline_months < 18 and len(inp.modules) > 5:
        _append(
            "REC_TIMELINE_TIGHT_PHASED",
            "REC_TIMELINE_TIGHT_PHASED",
            [_fact("FACT_TIMELINE", months=inp.migration_timeline_months), _fact("FACT_MODULE_COUNT", count=len(inp.modules))],
        )

    pain_point_categories = detect_pain_point_categories(inp.pain_points)
    pain_point_fact = inp.pain_points.strip()
    pain_point_rules = [
        ("financial_close", "REC_PAIN_FIN_CLOSE"),
        ("performance", "REC_PAIN_PERFORMANCE"),
        ("upgrade", "REC_PAIN_UPGRADE_COMPAT"),
        ("integration", "REC_PAIN_INTEGRATION"),
        ("ai_data", "REC_PAIN_AI_DATA"),
        ("security", "REC_PAIN_SECURITY"),
    ]
    for category, rule_id in pain_point_rules:
        if category not in pain_point_categories:
            continue
        _append(rule_id, rule_id, [pain_point_fact] if pain_point_fact else [])

    # 저위험/고성숙 케이스에서도 실행 가능한 액션이 최소 3개는 제공되도록 보강한다.
    baseline_candidates = [
        ("REC_LOW_RISK_GOVERNANCE", "REC_LOW_RISK_GOVERNANCE"),
        ("REC_LOW_RISK_KPI_MONITORING", "REC_LOW_RISK_KPI_MONITORING"),
        ("REC_LOW_RISK_ROADMAP", "REC_LOW_RISK_ROADMAP"),
    ]
    existing_rule_ids = {rid for trace in traces for rid in trace.rule_ids}
    baseline_minimum = 2 if calc.risk_level == "Low" else 0
    baseline_added = 0
    for msg_key, rule_id in baseline_candidates:
        if len(traces) >= 3 and baseline_added >= baseline_minimum:
            break
        if rule_id in existing_rule_ids:
            continue
        _append(msg_key, rule_id, [base_score_fact])
        existing_rule_ids.add(rule_id)
        baseline_added += 1

    if not traces:
        _append(
            "REC_DEFAULT_BASELINE",
            "REC_DEFAULT_BASELINE",
            [base_score_fact],
        )

    return traces
