"""Ruleset calibration engine with constrained search and holdout validation."""

from __future__ import annotations

import copy
import os
from dataclasses import dataclass
from typing import Any

from models.schemas import CustomerInput, ModuleInfo
from services.cost_calculator import run_calculation
from services.data_quality import validate_calibration_rows
from services.ruleset_loader import RulesetProfile

TUNABLE_TCO_KEYS = [
    "infra_cost_per_user",
    "custom_maintenance_per_program",
    "license_cost_per_user",
    "db_cost_per_gb",
]


@dataclass(frozen=True)
class BacktestMetrics:
    """Backtest quality metrics."""

    mape_tco: float
    risk_mismatch_rate: float
    risk_agreement: float


@dataclass(frozen=True)
class CalibrationResult:
    """Calibration result for ruleset generation."""

    ok: bool
    loss: float
    tuned_ruleset: dict[str, Any]
    train_metrics: BacktestMetrics
    holdout_metrics: BacktestMetrics
    warnings: list[str]
    errors: list[str]


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(str(value).strip())
    except Exception:
        return default


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(str(value).strip()))
    except Exception:
        return default


def _weights() -> tuple[float, float]:
    w_tco = _as_float(os.getenv("CALIBRATION_WEIGHT_TCO", "0.7"), 0.7)
    w_risk = _as_float(os.getenv("CALIBRATION_WEIGHT_RISK", "0.3"), 0.3)
    total = w_tco + w_risk
    if total <= 0:
        return 0.7, 0.3
    return w_tco / total, w_risk / total


def _grid_params() -> tuple[float, float, float]:
    low = 0.60
    high = 1.60
    step = 0.05
    return low, high, step


def _iter_multipliers() -> list[float]:
    low, high, step = _grid_params()
    values: list[float] = []
    current = low
    while current <= high + 1e-9:
        values.append(round(current, 2))
        current += step
    return values


def _row_to_input(row: dict[str, Any]) -> CustomerInput:
    return CustomerInput(
        company_name=str(row["company_id"]),
        industry=str(row["industry"]),
        erp_version=str(row["erp_version"]),
        db_type=str(row["db_type"]),
        db_size_gb=_as_float(row.get("db_size_gb", 500.0), 500.0),
        num_users=_as_int(row["num_users"], 1),
        num_custom_programs=_as_int(row["num_custom_programs"], 0),
        custom_code_ratio=_as_float(row["custom_code_ratio"], 0.0),
        modules=[ModuleInfo(module_name="FI", customization_level="medium")],
        annual_it_budget_krw=max(_as_float(row.get("annual_it_budget_krw", 10.0), 10.0), 0.1),
        pain_points=str(row.get("pain_points", "")),
        migration_timeline_months=_as_int(row["migration_duration_months"], 12),
    )


def _mape(actual: list[float], predicted: list[float]) -> float:
    if not actual:
        return 0.0
    ape_values: list[float] = []
    for a, p in zip(actual, predicted):
        denom = max(abs(a), 1e-6)
        ape_values.append(abs(a - p) / denom)
    return sum(ape_values) / len(ape_values)


def _risk_mismatch(actual: list[str], predicted: list[str]) -> float:
    if not actual:
        return 0.0
    mismatches = sum(1 for a, p in zip(actual, predicted) if a != p)
    return mismatches / len(actual)


def _metrics_from_predictions(
    actual_current_tco: list[float],
    actual_projected_tco: list[float],
    actual_risk: list[str],
    pred_current_tco: list[float],
    pred_projected_tco: list[float],
    pred_risk: list[str],
) -> BacktestMetrics:
    mape_current = _mape(actual_current_tco, pred_current_tco)
    mape_projected = _mape(actual_projected_tco, pred_projected_tco)
    mape_tco = (mape_current + mape_projected) / 2
    mismatch = _risk_mismatch(actual_risk, pred_risk)
    return BacktestMetrics(
        mape_tco=round(mape_tco, 6),
        risk_mismatch_rate=round(mismatch, 6),
        risk_agreement=round(1.0 - mismatch, 6),
    )


def _evaluate_rows(rows: list[dict[str, Any]], profile: RulesetProfile) -> BacktestMetrics:
    actual_current: list[float] = []
    actual_projected: list[float] = []
    actual_risk: list[str] = []
    pred_current: list[float] = []
    pred_projected: list[float] = []
    pred_risk: list[str] = []

    for row in rows:
        inp = _row_to_input(row)
        result = run_calculation(inp, ruleset_profile=profile)
        actual_current.append(_as_float(row["actual_current_tco"], 0.0))
        actual_projected.append(_as_float(row["actual_projected_tco"], 0.0))
        actual_risk.append(str(row["actual_risk_level"]))
        pred_current.append(result.current_annual_tco)
        pred_projected.append(result.projected_tco_after_migration)
        pred_risk.append(result.risk_level)

    return _metrics_from_predictions(
        actual_current,
        actual_projected,
        actual_risk,
        pred_current,
        pred_projected,
        pred_risk,
    )


def evaluate_rows(rows: list[dict[str, Any]], profile: RulesetProfile) -> BacktestMetrics:
    """Public wrapper for row-level evaluation metrics."""
    return _evaluate_rows(rows, profile)


def split_train_holdout(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    ordered = sorted(rows, key=lambda r: str(r.get("company_id", "")))
    if len(ordered) < 5:
        return ordered, []
    cut = max(1, int(len(ordered) * 0.8))
    return ordered[:cut], ordered[cut:]


def _apply_tco_multiplier(config: dict[str, Any], multiplier: float) -> dict[str, Any]:
    new_config = copy.deepcopy(config)
    tco_section = dict(new_config.get("tco", {}))
    for key in TUNABLE_TCO_KEYS:
        if key in tco_section:
            tco_section[key] = round(float(tco_section[key]) * multiplier, 10)
    new_config["tco"] = tco_section
    return new_config


def _to_profile(profile: RulesetProfile, config: dict[str, Any], source: str = "generated") -> RulesetProfile:
    quality = config.get("calibration_quality", {})
    if not isinstance(quality, dict):
        quality = {}
    return RulesetProfile(
        profile_id=str(config.get("profile_id", profile.profile_id)),
        profile_source=source,
        ruleset_version=str(config.get("ruleset_version", profile.ruleset_version)),
        calibration_quality={k: float(v) for k, v in quality.items()},
        config=config,
    )


def calibrate_ruleset(rows: list[dict[str, Any]], base_profile: RulesetProfile) -> CalibrationResult:
    """Calibrate ruleset coefficients using constrained grid search."""
    quality = validate_calibration_rows(rows)
    if not quality.ok:
        empty_metrics = BacktestMetrics(0.0, 0.0, 1.0)
        return CalibrationResult(
            ok=False,
            loss=1.0,
            tuned_ruleset=base_profile.config,
            train_metrics=empty_metrics,
            holdout_metrics=empty_metrics,
            warnings=quality.warnings,
            errors=quality.errors,
        )

    train_rows, holdout_rows = split_train_holdout(rows)
    weight_tco, weight_risk = _weights()
    best_loss = float("inf")
    best_config = base_profile.config
    best_train = BacktestMetrics(0.0, 0.0, 1.0)
    best_holdout = BacktestMetrics(0.0, 0.0, 1.0)

    for multiplier in _iter_multipliers():
        candidate = _apply_tco_multiplier(base_profile.config, multiplier)
        candidate["profile_id"] = base_profile.profile_id
        candidate["ruleset_version"] = base_profile.ruleset_version

        candidate_profile = _to_profile(base_profile, candidate, source="generated")
        train_metrics = _evaluate_rows(train_rows, candidate_profile)
        holdout_metrics = (
            _evaluate_rows(holdout_rows, candidate_profile)
            if holdout_rows
            else train_metrics
        )
        loss = (
            weight_tco * train_metrics.mape_tco
            + weight_risk * train_metrics.risk_mismatch_rate
        )

        if loss < best_loss:
            best_loss = loss
            best_config = candidate
            best_train = train_metrics
            best_holdout = holdout_metrics

    best_config = copy.deepcopy(best_config)
    best_config["calibration_quality"] = {
        "mape_tco": best_holdout.mape_tco,
        "risk_agreement": best_holdout.risk_agreement,
    }

    # 품질 임계치: Holdout MAPE 0.5 이하, Risk agreement 0.4 이상
    quality_ok = best_holdout.mape_tco <= 0.5 and best_holdout.risk_agreement >= 0.4
    errors = [] if quality_ok else ["calibration quality threshold not met"]

    return CalibrationResult(
        ok=quality_ok,
        loss=round(best_loss, 6),
        tuned_ruleset=best_config,
        train_metrics=best_train,
        holdout_metrics=best_holdout,
        warnings=quality.warnings,
        errors=errors,
    )
