"""Data quality gate for calibration/backtest datasets."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any
from config.settings import settings


REQUIRED_COLUMNS = [
    "company_id",
    "industry",
    "erp_version",
    "db_type",
    "num_users",
    "num_custom_programs",
    "custom_code_ratio",
    "actual_current_tco",
    "actual_projected_tco",
    "actual_risk_level",
    "migration_duration_months",
]


@dataclass(frozen=True)
class DataQualityResult:
    """Result of dataset quality validation."""

    ok: bool
    warnings: list[str]
    errors: list[str]
    accepted_rows: int


def _as_float(value: Any) -> float | None:
    try:
        return float(str(value).strip())
    except Exception:
        return None


def _as_int(value: Any) -> int | None:
    try:
        return int(float(str(value).strip()))
    except Exception:
        return None


def _min_samples_threshold() -> int:
    return max(1, settings.CALIBRATION_MIN_SAMPLES)


def validate_calibration_rows(rows: list[dict[str, Any]]) -> DataQualityResult:
    """Validate calibration rows and enforce minimum sample size."""
    warnings: list[str] = []
    errors: list[str] = []
    accepted_rows = 0

    if not rows:
        return DataQualityResult(False, warnings, ["empty dataset"], 0)

    for idx, row in enumerate(rows, start=1):
        missing = [col for col in REQUIRED_COLUMNS if col not in row or str(row[col]).strip() == ""]
        if missing:
            errors.append(f"row {idx}: missing columns {', '.join(missing)}")
            continue

        num_users = _as_int(row["num_users"])
        num_custom_programs = _as_int(row["num_custom_programs"])
        timeline = _as_int(row["migration_duration_months"])
        custom_ratio = _as_float(row["custom_code_ratio"])
        actual_current_tco = _as_float(row["actual_current_tco"])
        actual_projected_tco = _as_float(row["actual_projected_tco"])

        if None in (num_users, num_custom_programs, timeline, custom_ratio, actual_current_tco, actual_projected_tco):
            errors.append(f"row {idx}: numeric conversion failed")
            continue

        if num_users <= 0 or num_custom_programs < 0 or timeline <= 0:
            errors.append(f"row {idx}: invalid integer range")
            continue

        if custom_ratio < 0 or custom_ratio > 100:
            errors.append(f"row {idx}: custom_code_ratio out of range")
            continue

        if actual_current_tco <= 0 or actual_projected_tco <= 0:
            errors.append(f"row {idx}: tco must be positive")
            continue

        # 극단값은 배제 대신 경고만 남겨 추후 판단 가능하게 함
        if custom_ratio > 95:
            warnings.append(f"row {idx}: extreme custom_code_ratio={custom_ratio}")
        if num_users > 200000:
            warnings.append(f"row {idx}: extreme num_users={num_users}")
        if actual_current_tco > 10000:
            warnings.append(f"row {idx}: extreme actual_current_tco={actual_current_tco}")

        accepted_rows += 1

    min_samples = _min_samples_threshold()
    if accepted_rows < min_samples:
        errors.append(
            f"insufficient samples: accepted={accepted_rows}, required={min_samples}"
        )

    return DataQualityResult(
        ok=not errors,
        warnings=warnings,
        errors=errors,
        accepted_rows=accepted_rows,
    )
