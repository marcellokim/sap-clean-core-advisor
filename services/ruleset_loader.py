"""Ruleset loader with generated > industry > base fallback order."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from services.config_utils import load_json_yaml
from services.industry_mapper import resolve_industry_profile
from config.settings import settings

DEFAULT_RULESET_DIR = Path(__file__).resolve().parent.parent / "config" / "rulesets"


@dataclass(frozen=True)
class RulesetProfile:
    """Resolved ruleset profile for deterministic calculations."""

    profile_id: str
    profile_source: str  # base | industry | generated
    ruleset_version: str
    calibration_quality: dict[str, float]
    config: dict[str, Any]


@dataclass(frozen=True)
class RulesetResolution:
    """Ruleset plus warnings from mapping/validation fallback."""

    profile: RulesetProfile
    warnings: list[str]


def _ruleset_root() -> Path:
    return Path(settings.RULESET_DIR)


def _generated_root() -> Path:
    if settings.RULESET_GENERATED_DIR:
        return Path(settings.RULESET_GENERATED_DIR)
    return _ruleset_root() / "generated"


def _get_path_candidates(canonical_profile: str) -> list[tuple[str, Path]]:
    root = _ruleset_root()
    generated_root = _generated_root()
    allow_generated = settings.RULESET_ALLOW_GENERATED
    candidates: list[tuple[str, Path]] = []
    if allow_generated:
        candidates.append(("generated", generated_root / f"{canonical_profile}.yaml"))
    candidates.extend(
        [
            ("industry", root / "industries" / f"{canonical_profile}.yaml"),
            ("base", root / "base.yaml"),
        ]
    )
    return candidates


def _required_top_level_keys() -> set[str]:
    return {
        "ruleset_version",
        "profile_id",
        "module_weights",
        "customization_score",
        "score_weights",
        "erp_version_scores",
        "database_scores",
        "formula",
        "tco",
        "risk_thresholds",
    }


def _validate_ruleset_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = _required_top_level_keys() - set(payload.keys())
    if missing:
        errors.append(f"missing keys: {', '.join(sorted(missing))}")

    for section in ("tco", "risk_thresholds", "formula", "score_weights"):
        if not isinstance(payload.get(section), dict):
            errors.append(f"section `{section}` must be object")
    return errors


def _load_ruleset_from_path(path: Path, profile_source: str) -> RulesetProfile:
    payload = load_json_yaml(path)
    errors = _validate_ruleset_payload(payload)
    if errors:
        joined = "; ".join(errors)
        raise ValueError(f"Invalid ruleset {path}: {joined}")
    calibration_quality = payload.get("calibration_quality", {})
    if not isinstance(calibration_quality, dict):
        calibration_quality = {}
    return RulesetProfile(
        profile_id=str(payload.get("profile_id", "base")),
        profile_source=profile_source,
        ruleset_version=str(payload["ruleset_version"]),
        calibration_quality={k: float(v) for k, v in calibration_quality.items()},
        config=payload,
    )


@lru_cache(maxsize=32)
def resolve_ruleset_profile(industry: str) -> RulesetResolution:
    """Resolve ruleset by precedence: generated > industry > base."""
    warnings: list[str] = []
    industry_resolution = resolve_industry_profile(industry)
    canonical_profile = industry_resolution.profile_key

    if not industry_resolution.matched:
        warnings.append("INDUSTRY_MAPPING_FALLBACK_TO_BASE")
        canonical_profile = "base"

    for source, path in _get_path_candidates(canonical_profile):
        if not path.exists():
            continue
        try:
            profile = _load_ruleset_from_path(path, source)
            return RulesetResolution(profile=profile, warnings=warnings)
        except Exception:
            warnings.append(f"RULESET_INVALID_{source.upper()}_{canonical_profile.upper()}")
            continue

    # 최후 fallback (base 경로 이상 시 최소 안전 기본값)
    fallback_profile = RulesetProfile(
        profile_id="base",
        profile_source="base",
        ruleset_version="fallback.v1",
        calibration_quality={},
        config={
            "ruleset_version": "fallback.v1",
            "profile_id": "base",
            "module_weights": {},
            "customization_score": {"low": 0.3, "medium": 0.6, "high": 1.0},
            "score_weights": {
                "custom_code": 0.35,
                "erp_version": 0.25,
                "database": 0.15,
                "module_complexity": 0.25,
            },
            "erp_version_scores": {"ECC 6.0": 40.0},
            "database_scores": {"hana": 90.0, "oracle": 45.0, "sql": 40.0, "other": 35.0},
            "formula": {
                "custom_code_multiplier": 1.5,
                "custom_program_density_penalty_rate": 0.08,
                "custom_program_density_penalty_cap": 10.0,
                "module_severity_multiplier": 50.0,
                "module_count_penalty_per_module": 3.0,
                "module_count_penalty_cap": 30.0,
                "module_complexity_empty_score": 80.0,
                "high_custom_module_penalty": 4.0,
                "high_custom_module_penalty_cap": 12.0,
                "database_size_penalty_per_tb": 3.0,
                "database_size_penalty_cap": 15.0,
                "hana_size_penalty_multiplier": 0.35,
            },
            "tco": {
                "infra_cost_per_user": 0.0003,
                "custom_maintenance_per_program": 0.0005,
                "license_cost_per_user": 0.0008,
                "db_cost_per_gb": 0.00002,
                "cloud_infra_savings_rate": 0.35,
                "clean_core_custom_savings_rate": 0.5,
                "s4_license_change_rate": 1.1,
            },
            "risk_thresholds": {
                "custom_ratio_medium": 30.0,
                "custom_ratio_high": 60.0,
                "timeline_months_tight": 12,
                "timeline_custom_programs_tight": 200,
                "db_size_large_gb": 5000.0,
                "budget_ratio_medium": 0.7,
                "budget_ratio_high": 1.0,
                "risk_level_score_high": 30.0,
                "risk_level_score_medium": 60.0,
                "risk_factor_count_high": 4,
                "risk_factor_count_medium": 2,
            },
        },
    )
    warnings.append("RULESET_HARD_FALLBACK_APPLIED")
    return RulesetResolution(profile=fallback_profile, warnings=warnings)
