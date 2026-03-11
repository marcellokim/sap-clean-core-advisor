#!/usr/bin/env python3
# ruff: noqa: E402
"""Evaluate deterministic demo benchmark cases and emit calibration artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import pstdev
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from models.schemas import CustomerInput
from services.cost_calculator import run_calculation
from services.domain.recommendation_engine import extract_recommendations
from services.ruleset_loader import resolve_ruleset_profile

DEFAULT_FIXTURE_PATH = PROJECT_ROOT / "tests" / "fixtures" / "demo_benchmark.yaml"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "artifacts" / "calibration"


@dataclass(frozen=True)
class ScoreRange:
    """Expected inclusive score range for a benchmark case."""

    minimum: float
    maximum: float

    def contains(self, value: float) -> bool:
        return self.minimum <= value <= self.maximum

    def distance(self, value: float) -> float:
        if self.contains(value):
            return 0.0
        if value < self.minimum:
            return round(self.minimum - value, 1)
        return round(value - self.maximum, 1)

    def label(self) -> str:
        if self.minimum == self.maximum:
            return f"{self.minimum:.1f}"
        return f"{self.minimum:.1f}-{self.maximum:.1f}"


@dataclass(frozen=True)
class BenchmarkCase:
    """Structured benchmark input + expectations."""

    case_id: str
    customer_input: CustomerInput
    score_range: ScoreRange | None
    expected_risk_level: str | None
    expected_rule_ids_any: tuple[str, ...]
    expected_recommendation_ids_any: tuple[str, ...]
    notes: str


_SIGNAL_METRIC_ALIASES = {
    "score": "clean_core_score",
    "clean_core_score": "clean_core_score",
    "current_tco": "current_annual_tco",
    "current_annual_tco": "current_annual_tco",
    "projected_tco": "projected_tco_after_migration",
    "projected_annual_tco": "projected_tco_after_migration",
    "projected_tco_after_migration": "projected_tco_after_migration",
    "tco_savings": "tco_savings_3yr",
    "tco_savings_3yr": "tco_savings_3yr",
}

_SIGNAL_METRIC_LABELS = {
    "clean_core_score": "score",
    "current_annual_tco": "current annual TCO",
    "projected_tco_after_migration": "projected annual TCO",
    "tco_savings_3yr": "3-year TCO savings",
}

_HEADROOM_BOUND_ALIASES = {
    "min": "min",
    "minimum": "min",
    "lower": "min",
    "lower_bound": "min",
    "max": "max",
    "maximum": "max",
    "upper": "max",
    "upper_bound": "max",
}


def _read_benchmark_payload(path: Path) -> Any:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"Empty benchmark fixture: {path}")
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid benchmark fixture YAML at {path}: {exc}") from exc


def _parse_score_range(raw: Any, case_id: str) -> ScoreRange | None:
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        value = float(raw)
        return ScoreRange(value, value)
    if isinstance(raw, str):
        cleaned = raw.strip()
        if not cleaned:
            return None
        if "-" in cleaned:
            parts = [part.strip() for part in cleaned.split("-", maxsplit=1)]
            if len(parts) == 2:
                return ScoreRange(float(parts[0]), float(parts[1]))
        value = float(cleaned)
        return ScoreRange(value, value)
    if isinstance(raw, list) and len(raw) == 2:
        return ScoreRange(float(raw[0]), float(raw[1]))
    if isinstance(raw, dict):
        if "min" in raw and "max" in raw:
            return ScoreRange(float(raw["min"]), float(raw["max"]))
        if "minimum" in raw and "maximum" in raw:
            return ScoreRange(float(raw["minimum"]), float(raw["maximum"]))
    raise ValueError(f"Invalid expected_score_range for case `{case_id}`: {raw!r}")


def _normalize_expected_ids(raw: Any, field_name: str, case_id: str) -> tuple[str, ...]:
    if raw is None:
        return ()
    if isinstance(raw, str):
        values = [raw]
    elif isinstance(raw, list):
        values = raw
    else:
        raise ValueError(f"{field_name} for case `{case_id}` must be a string or list")

    normalized: list[str] = []
    for value in values:
        text = str(value).strip()
        if text:
            normalized.append(text)
    return tuple(normalized)


def load_benchmark_cases(path: Path) -> tuple[list[BenchmarkCase], dict[str, Any]]:
    payload = _read_benchmark_payload(path)

    metadata: dict[str, Any] = {}
    if isinstance(payload, list):
        cases_raw = payload
    elif isinstance(payload, dict):
        metadata = {key: value for key, value in payload.items() if key not in {"cases", "benchmarks", "items"}}
        nested_metadata = metadata.get("metadata")
        if isinstance(nested_metadata, dict):
            merged_metadata = {**metadata, **nested_metadata}
            merged_metadata.pop("metadata", None)
            metadata = merged_metadata
        cases_raw = payload.get("cases", payload.get("benchmarks", payload.get("items", [])))
    else:
        raise ValueError("Benchmark fixture must be a list or object with `cases`")

    if not isinstance(cases_raw, list) or not cases_raw:
        raise ValueError("Benchmark fixture must define at least one case")

    cases: list[BenchmarkCase] = []
    for index, raw_case in enumerate(cases_raw, start=1):
        if not isinstance(raw_case, dict):
            raise ValueError(f"Case #{index} must be an object")
        case_id = str(raw_case.get("case_id") or raw_case.get("id") or f"case-{index:02d}")
        input_payload = raw_case.get("input")
        if not isinstance(input_payload, dict):
            raise ValueError(f"Case `{case_id}` is missing an object `input`")

        cases.append(
            BenchmarkCase(
                case_id=case_id,
                customer_input=CustomerInput(**input_payload),
                score_range=_parse_score_range(raw_case.get("expected_score_range"), case_id),
                expected_risk_level=str(raw_case["expected_risk_level"]).strip() if raw_case.get("expected_risk_level") else None,
                expected_rule_ids_any=_normalize_expected_ids(
                    raw_case.get("expected_rule_ids_any"),
                    "expected_rule_ids_any",
                    case_id,
                ),
                expected_recommendation_ids_any=_normalize_expected_ids(
                    raw_case.get("expected_recommendation_ids_any"),
                    "expected_recommendation_ids_any",
                    case_id,
                ),
                notes=str(raw_case.get("notes", "")).strip(),
            )
        )
    return cases, metadata


def _rate_payload(values: list[bool | None]) -> dict[str, Any]:
    filtered = [value for value in values if value is not None]
    hits = sum(1 for value in filtered if value)
    total = len(filtered)
    rate = round(hits / total, 4) if total else None
    return {"hits": hits, "total": total, "rate": rate}


def _format_rate(metric: dict[str, Any]) -> str:
    total = int(metric["total"])
    if total == 0:
        return "N/A"
    rate = float(metric["rate"])
    return f"{metric['hits']}/{total} ({rate * 100:.1f}%)"


def _check_label(value: bool | None) -> str:
    if value is None:
        return "N/A"
    return "PASS" if value else "FAIL"


def _safe_relative(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def _numeric_summary(values: list[float], *, digits: int) -> dict[str, Any]:
    if not values:
        return {
            "count": 0,
            "average": None,
            "min": None,
            "max": None,
            "span": None,
            "stddev": None,
        }

    return {
        "count": len(values),
        "average": round(sum(values) / len(values), digits),
        "min": round(min(values), digits),
        "max": round(max(values), digits),
        "span": round(max(values) - min(values), digits),
        "stddev": round(pstdev(values), digits) if len(values) > 1 else 0.0,
    }


def _resolve_metric_name(raw_metric: Any) -> str:
    metric_key = str(raw_metric or "").strip().lower()
    metric = _SIGNAL_METRIC_ALIASES.get(metric_key)
    if not metric:
        allowed = ", ".join(sorted(_SIGNAL_METRIC_ALIASES))
        raise ValueError(f"Unsupported signal assertion metric `{raw_metric}`. Allowed: {allowed}")
    return metric


def _resolve_headroom_bound(raw_bound: Any) -> str:
    bound_key = str(raw_bound or "").strip().lower()
    bound = _HEADROOM_BOUND_ALIASES.get(bound_key)
    if not bound:
        allowed = ", ".join(sorted(_HEADROOM_BOUND_ALIASES))
        raise ValueError(f"Unsupported headroom guardrail bound `{raw_bound}`. Allowed: {allowed}")
    return bound


def _parse_signal_assertions(metadata: dict[str, Any], case_ids: set[str]) -> dict[str, list[dict[str, Any]]]:
    raw = (
        metadata.get("signal_assertions")
        or metadata.get("benchmark_assertions")
        or metadata.get("benchmark_expectations")
        or {}
    )
    if raw and not isinstance(raw, dict):
        raise ValueError("`signal_assertions` must be an object when provided")
    raw = raw if isinstance(raw, dict) else {}

    tuning_expectations = metadata.get("tuning_expectations") or {}
    if tuning_expectations and not isinstance(tuning_expectations, dict):
        raise ValueError("`tuning_expectations` must be an object when provided")

    pairwise_items = list(raw.get("pairwise_gap_assertions", []))
    headroom_items = raw.get("headroom_guardrails", [])
    if not isinstance(pairwise_items, list):
        raise ValueError("`signal_assertions.pairwise_gap_assertions` must be a list")
    if not isinstance(headroom_items, list):
        raise ValueError("`signal_assertions.headroom_guardrails` must be a list")

    closest_score_pairs = tuning_expectations.get("closest_score_pairs", [])
    if not isinstance(closest_score_pairs, list):
        raise ValueError("`tuning_expectations.closest_score_pairs` must be a list")
    for index, item in enumerate(closest_score_pairs, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"tuning_expectations.closest_score_pairs[{index}] must be an object")
        pairwise_items.append(
            {
                "metric": "clean_core_score",
                "higher_case_id": item.get("right_case_id"),
                "lower_case_id": item.get("left_case_id"),
                "min_gap": item.get("minimum_gap", item.get("min_gap", 0.0)),
                "reason": item.get("rationale") or item.get("reason") or item.get("notes"),
                "source": "tuning_expectations.closest_score_pairs",
            }
        )

    pairwise_assertions: list[dict[str, Any]] = []
    for index, item in enumerate(pairwise_items, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"pairwise_gap_assertions[{index}] must be an object")
        metric = _resolve_metric_name(item.get("metric"))
        higher_case_id = str(
            item.get("higher_case_id")
            or item.get("greater_case_id")
            or item.get("left_case_id")
            or ""
        ).strip()
        lower_case_id = str(
            item.get("lower_case_id")
            or item.get("lesser_case_id")
            or item.get("right_case_id")
            or ""
        ).strip()
        if not higher_case_id or not lower_case_id:
            raise ValueError(
                f"pairwise_gap_assertions[{index}] must define higher_case_id and lower_case_id"
            )
        missing_case_ids = [case_id for case_id in (higher_case_id, lower_case_id) if case_id not in case_ids]
        if missing_case_ids:
            raise ValueError(
                f"pairwise_gap_assertions[{index}] references unknown case ids: {', '.join(missing_case_ids)}"
            )
        pairwise_assertions.append(
            {
                "metric": metric,
                "higher_case_id": higher_case_id,
                "lower_case_id": lower_case_id,
                "min_gap": float(item.get("min_gap", 0.0)),
                "reason": str(item.get("reason") or item.get("notes") or "").strip(),
                "source": str(item.get("source") or "signal_assertions.pairwise_gap_assertions"),
            }
        )

    headroom_assertions: list[dict[str, Any]] = []
    for index, item in enumerate(headroom_items, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"headroom_guardrails[{index}] must be an object")
        case_id = str(item.get("case_id") or "").strip()
        if not case_id:
            raise ValueError(f"headroom_guardrails[{index}] must define case_id")
        if case_id not in case_ids:
            raise ValueError(f"headroom_guardrails[{index}] references unknown case id `{case_id}`")
        headroom_assertions.append(
            {
                "case_id": case_id,
                "bound": _resolve_headroom_bound(item.get("bound") or item.get("side")),
                "minimum": float(item.get("minimum", item.get("min_headroom", 0.0))),
                "reason": str(item.get("reason") or item.get("notes") or "").strip(),
                "source": "signal_assertions.headroom_guardrails",
            }
        )

    return {
        "pairwise_gap_assertions": pairwise_assertions,
        "headroom_guardrails": headroom_assertions,
    }


def _evaluate_signal_assertions(results: list[dict[str, Any]], metadata: dict[str, Any]) -> dict[str, Any]:
    case_index = {str(row["case_id"]): row for row in results}
    assertions = _parse_signal_assertions(metadata, set(case_index))

    pairwise_results: list[dict[str, Any]] = []
    headroom_results: list[dict[str, Any]] = []
    pass_values: list[bool] = []

    for item in assertions["pairwise_gap_assertions"]:
        metric = item["metric"]
        digits = 1 if metric == "clean_core_score" else 2
        higher_value = float(case_index[item["higher_case_id"]]["actual"][metric])
        lower_value = float(case_index[item["lower_case_id"]]["actual"][metric])
        actual_gap = round(higher_value - lower_value, digits)
        passed = actual_gap >= item["min_gap"]
        pass_values.append(passed)
        pairwise_results.append(
            {
                **item,
                "metric_label": _SIGNAL_METRIC_LABELS[metric],
                "higher_value": round(higher_value, digits),
                "lower_value": round(lower_value, digits),
                "actual_gap": actual_gap,
                "passed": passed,
            }
        )

    for item in assertions["headroom_guardrails"]:
        headroom_field = "score_headroom_to_min" if item["bound"] == "min" else "score_headroom_to_max"
        row = case_index[item["case_id"]]
        actual_headroom = round(float(row["checks"][headroom_field]), 1)
        passed = actual_headroom >= item["minimum"]
        pass_values.append(passed)
        headroom_results.append(
            {
                **item,
                "actual_headroom": actual_headroom,
                "actual_score": round(float(row["actual"]["clean_core_score"]), 1),
                "expected_score_range": row["expected"]["score_range"],
                "passed": passed,
            }
        )

    total = len(pass_values)
    passed = sum(1 for value in pass_values if value)
    return {
        "defined": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round(passed / total, 4) if total else None,
        "all_passed": all(pass_values) if total else True,
        "pairwise_gap_assertions": pairwise_results,
        "headroom_guardrails": headroom_results,
    }


def _build_tuning_signals(results: list[dict[str, Any]], *, top_n: int = 3) -> dict[str, Any]:
    score_values = [float(row["actual"]["clean_core_score"]) for row in results]
    current_tco_values = [float(row["actual"]["current_annual_tco"]) for row in results]
    projected_tco_values = [float(row["actual"]["projected_tco_after_migration"]) for row in results]
    savings_values = [float(row["actual"]["tco_savings_3yr"]) for row in results]

    sorted_by_score = sorted(
        results,
        key=lambda row: (float(row["actual"]["clean_core_score"]), row["case_id"]),
    )
    closest_score_pairs: list[dict[str, Any]] = []
    for left, right in zip(sorted_by_score, sorted_by_score[1:]):
        left_score = float(left["actual"]["clean_core_score"])
        right_score = float(right["actual"]["clean_core_score"])
        closest_score_pairs.append(
            {
                "left_case_id": left["case_id"],
                "right_case_id": right["case_id"],
                "left_score": round(left_score, 1),
                "right_score": round(right_score, 1),
                "gap": round(right_score - left_score, 1),
            }
        )
    closest_score_pairs.sort(key=lambda item: (item["gap"], item["left_case_id"], item["right_case_id"]))

    def _narrowest_headroom(field_name: str) -> list[dict[str, Any]]:
        eligible = [
            {
                "case_id": row["case_id"],
                "headroom": float(row["checks"][field_name]),
                "actual_score": round(float(row["actual"]["clean_core_score"]), 1),
                "expected_score_range": row["expected"]["score_range"],
            }
            for row in results
            if row["checks"][field_name] is not None
        ]
        eligible.sort(key=lambda item: (item["headroom"], item["case_id"]))
        return eligible[:top_n]

    return {
        "score_distribution": _numeric_summary(score_values, digits=1),
        "current_annual_tco_distribution": _numeric_summary(current_tco_values, digits=2),
        "projected_annual_tco_distribution": _numeric_summary(projected_tco_values, digits=2),
        "tco_savings_3yr_distribution": _numeric_summary(savings_values, digits=2),
        "closest_score_pairs": closest_score_pairs[:top_n],
        "narrowest_score_headroom_to_min": _narrowest_headroom("score_headroom_to_min"),
        "narrowest_score_headroom_to_max": _narrowest_headroom("score_headroom_to_max"),
    }


def evaluate_cases(
    cases: list[BenchmarkCase],
    *,
    lang: str,
    metadata: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    results: list[dict[str, Any]] = []
    industry_groups: dict[str, dict[str, Any]] = {}
    metadata = metadata or {}

    for case in cases:
        resolution = resolve_ruleset_profile(case.customer_input.industry)
        calc = run_calculation(case.customer_input, ruleset_profile=resolution.profile)
        recommendation_traces = extract_recommendations(calc, case.customer_input, lang=lang)
        recommendation_rule_ids = list(
            dict.fromkeys(
                rule_id
                for trace in recommendation_traces
                for rule_id in trace.rule_ids
            )
        )

        score_hit = case.score_range.contains(calc.clean_core_score) if case.score_range else None
        risk_match = (
            calc.risk_level == case.expected_risk_level
            if case.expected_risk_level
            else None
        )
        matched_rule_ids = [
            rule_id for rule_id in case.expected_rule_ids_any if rule_id in calc.applied_rule_ids
        ]
        matched_recommendation_ids = [
            rule_id
            for rule_id in case.expected_recommendation_ids_any
            if rule_id in recommendation_rule_ids
        ]
        rule_match_any = bool(matched_rule_ids) if case.expected_rule_ids_any else None
        recommendation_match_any = (
            bool(matched_recommendation_ids) if case.expected_recommendation_ids_any else None
        )

        applicable_checks = [
            check
            for check in (score_hit, risk_match, rule_match_any, recommendation_match_any)
            if check is not None
        ]
        all_expected_checks_passed = all(applicable_checks) if applicable_checks else True

        case_result = {
            "case_id": case.case_id,
            "notes": case.notes,
            "input": case.customer_input.model_dump(),
            "expected": {
                "score_range": case.score_range.label() if case.score_range else None,
                "risk_level": case.expected_risk_level,
                "rule_ids_any": list(case.expected_rule_ids_any),
                "recommendation_ids_any": list(case.expected_recommendation_ids_any),
            },
            "actual": {
                "clean_core_score": calc.clean_core_score,
                "score_breakdown": calc.score_breakdown,
                "risk_level": calc.risk_level,
                "risk_factors": calc.risk_factors,
                "current_annual_tco": calc.current_annual_tco,
                "projected_tco_after_migration": calc.projected_tco_after_migration,
                "tco_savings_3yr": calc.tco_savings_3yr,
                "applied_rule_ids": calc.applied_rule_ids,
                "recommendation_rule_ids": recommendation_rule_ids,
                "recommendation_texts": [trace.text for trace in recommendation_traces],
                "ruleset_profile_id": calc.ruleset_profile_id,
                "ruleset_profile_source": calc.ruleset_profile_source,
                "ruleset_version": calc.ruleset_version,
                "calibration_quality": calc.calibration_quality,
                "resolution_warnings": resolution.warnings,
            },
            "checks": {
                "score_range_hit": score_hit,
                "score_distance_to_range": case.score_range.distance(calc.clean_core_score) if case.score_range else None,
                "score_headroom_to_min": round(calc.clean_core_score - case.score_range.minimum, 1) if case.score_range else None,
                "score_headroom_to_max": round(case.score_range.maximum - calc.clean_core_score, 1) if case.score_range else None,
                "risk_exact_match": risk_match,
                "rule_any_match": rule_match_any,
                "matched_rule_ids": matched_rule_ids,
                "missing_rule_ids": [
                    rule_id for rule_id in case.expected_rule_ids_any if rule_id not in matched_rule_ids
                ],
                "recommendation_any_match": recommendation_match_any,
                "matched_recommendation_ids": matched_recommendation_ids,
                "missing_recommendation_ids": [
                    rule_id
                    for rule_id in case.expected_recommendation_ids_any
                    if rule_id not in matched_recommendation_ids
                ],
                "all_expected_checks_passed": all_expected_checks_passed,
            },
        }
        results.append(case_result)

        profile_key = calc.ruleset_profile_id
        group = industry_groups.setdefault(
            profile_key,
            {
                "profile_id": profile_key,
                "profile_source": calc.ruleset_profile_source,
                "input_industries": set(),
                "scores": [],
                "risk_counts": Counter(),
            },
        )
        group["input_industries"].add(case.customer_input.industry)
        group["scores"].append(calc.clean_core_score)
        group["risk_counts"][calc.risk_level] += 1

    score_values = [row["checks"]["score_range_hit"] for row in results]
    risk_values = [row["checks"]["risk_exact_match"] for row in results]
    rule_values = [row["checks"]["rule_any_match"] for row in results]
    recommendation_values = [row["checks"]["recommendation_any_match"] for row in results]
    full_pass_values = [row["checks"]["all_expected_checks_passed"] for row in results]

    industry_summary: list[dict[str, Any]] = []
    for profile_id in sorted(industry_groups):
        group = industry_groups[profile_id]
        scores = [float(value) for value in group["scores"]]
        industry_summary.append(
            {
                "profile_id": profile_id,
                "profile_source": group["profile_source"],
                "input_industries": sorted(group["input_industries"]),
                "case_count": len(scores),
                "average_score": round(sum(scores) / len(scores), 1),
                "min_score": round(min(scores), 1),
                "max_score": round(max(scores), 1),
                "score_span": round(max(scores) - min(scores), 1),
                "risk_distribution": dict(sorted(group["risk_counts"].items())),
            }
        )

    metrics = {
        "score_range_hit_rate": _rate_payload(score_values),
        "risk_exact_match_rate": _rate_payload(risk_values),
        "rule_any_match_rate": _rate_payload(rule_values),
        "recommendation_coverage_rate": _rate_payload(recommendation_values),
        "fully_matched_case_rate": _rate_payload(full_pass_values),
    }
    signal_assertions = _evaluate_signal_assertions(results, metadata)
    metrics["signal_assertion_pass_rate"] = {
        "hits": signal_assertions["passed"],
        "total": signal_assertions["defined"],
        "rate": signal_assertions["pass_rate"],
    }

    summary = {
        "total_cases": len(results),
        "metrics": metrics,
        "tuning_signals": _build_tuning_signals(results),
        "signal_assertions": signal_assertions,
        "benchmark_gate_passed": bool(metrics["fully_matched_case_rate"]["hits"] == len(results) and signal_assertions["all_passed"]),
        "industry_differentiation_summary": industry_summary,
    }
    return results, summary


def _build_markdown_report(
    *,
    generated_at: str,
    fixture_path: Path,
    summary: dict[str, Any],
    results: list[dict[str, Any]],
) -> str:
    metrics = summary["metrics"]
    tuning_signals = summary["tuning_signals"]
    signal_metric = metrics.get("signal_assertion_pass_rate")
    signal_assertions = summary.get("signal_assertions")
    benchmark_gate_passed = summary.get("benchmark_gate_passed")
    lines = [
        "# Demo Benchmark Evaluation",
        "",
        f"- Generated at: `{generated_at}`",
        f"- Fixture: `{_safe_relative(fixture_path)}`",
        f"- Total cases: `{summary['total_cases']}`",
        "",
        "## Summary Metrics",
        "",
        f"- Score range hit rate: `{_format_rate(metrics['score_range_hit_rate'])}`",
        f"- Risk exact match rate: `{_format_rate(metrics['risk_exact_match_rate'])}`",
        f"- Rule any-match rate: `{_format_rate(metrics['rule_any_match_rate'])}`",
        f"- Recommendation coverage rate: `{_format_rate(metrics['recommendation_coverage_rate'])}`",
        f"- Fully matched case rate: `{_format_rate(metrics['fully_matched_case_rate'])}`",
    ]
    if signal_metric is not None:
        lines.append(f"- Signal assertion pass rate: `{_format_rate(signal_metric)}`")
    if benchmark_gate_passed is not None:
        lines.append(f"- Benchmark gate: `{'PASS' if benchmark_gate_passed else 'FAIL'}`")

    lines.extend(
        [
            "",
            "## Tuning Signals",
            "",
            "- Score dispersion: avg `{avg:.1f}`, min `{minv:.1f}`, max `{maxv:.1f}`, span `{span:.1f}`, stddev `{stddev:.1f}`".format(
            avg=tuning_signals["score_distribution"]["average"],
            minv=tuning_signals["score_distribution"]["min"],
            maxv=tuning_signals["score_distribution"]["max"],
            span=tuning_signals["score_distribution"]["span"],
            stddev=tuning_signals["score_distribution"]["stddev"],
        ),
            "- Current annual TCO dispersion: avg `{avg:.2f}`, min `{minv:.2f}`, max `{maxv:.2f}`, span `{span:.2f}`, stddev `{stddev:.2f}`".format(
            avg=tuning_signals["current_annual_tco_distribution"]["average"],
            minv=tuning_signals["current_annual_tco_distribution"]["min"],
            maxv=tuning_signals["current_annual_tco_distribution"]["max"],
            span=tuning_signals["current_annual_tco_distribution"]["span"],
            stddev=tuning_signals["current_annual_tco_distribution"]["stddev"],
        ),
            "- Projected annual TCO dispersion: avg `{avg:.2f}`, min `{minv:.2f}`, max `{maxv:.2f}`, span `{span:.2f}`, stddev `{stddev:.2f}`".format(
            avg=tuning_signals["projected_annual_tco_distribution"]["average"],
            minv=tuning_signals["projected_annual_tco_distribution"]["min"],
            maxv=tuning_signals["projected_annual_tco_distribution"]["max"],
            span=tuning_signals["projected_annual_tco_distribution"]["span"],
            stddev=tuning_signals["projected_annual_tco_distribution"]["stddev"],
        ),
            "",
            "### Closest Score Pairs",
            "",
        ]
    )

    for pair in tuning_signals["closest_score_pairs"]:
        lines.append(
            "- `{left}` `{left_score:.1f}` ↔ `{right}` `{right_score:.1f}` (gap `{gap:.1f}`)".format(
                left=pair["left_case_id"],
                left_score=pair["left_score"],
                right=pair["right_case_id"],
                right_score=pair["right_score"],
                gap=pair["gap"],
            )
        )

    lines.extend(["", "### Narrowest Score Headroom (to lower bound)", ""])
    for item in tuning_signals["narrowest_score_headroom_to_min"]:
        lines.append(
            "- `{case_id}` headroom `{headroom:.1f}` within expected `{score_range}`".format(
                case_id=item["case_id"],
                headroom=item["headroom"],
                score_range=item["expected_score_range"],
            )
        )

    lines.extend(["", "### Narrowest Score Headroom (to upper bound)", ""])
    for item in tuning_signals["narrowest_score_headroom_to_max"]:
        lines.append(
            "- `{case_id}` headroom `{headroom:.1f}` within expected `{score_range}`".format(
                case_id=item["case_id"],
                headroom=item["headroom"],
                score_range=item["expected_score_range"],
            )
        )

    if signal_assertions is not None:
        lines.extend(["", "## Signal Assertions", ""])
        if signal_assertions["defined"] == 0:
            lines.append("- No signal assertions defined.")
        else:
            lines.append(
                "- Overall: `{status}` (`{passed}/{total}` passed)".format(
                    status="PASS" if signal_assertions["all_passed"] else "FAIL",
                    passed=signal_assertions["passed"],
                    total=signal_assertions["defined"],
                )
            )
            if signal_assertions["pairwise_gap_assertions"]:
                lines.extend(["", "### Pairwise Gap Assertions", ""])
                for item in signal_assertions["pairwise_gap_assertions"]:
                    lines.append(
                        "- `{status}` {metric}: `{higher}` `{higher_value}` > `{lower}` `{lower_value}` (gap `{actual_gap}` vs expected `>= {min_gap}`)".format(
                            status="PASS" if item["passed"] else "FAIL",
                            metric=item["metric_label"],
                            higher=item["higher_case_id"],
                            higher_value=item["higher_value"],
                            lower=item["lower_case_id"],
                            lower_value=item["lower_value"],
                            actual_gap=item["actual_gap"],
                            min_gap=item["min_gap"],
                        )
                    )
                    if item["reason"]:
                        lines.append(f"  - Reason: {item['reason']}")
            if signal_assertions["headroom_guardrails"]:
                lines.extend(["", "### Headroom Guardrails", ""])
                for item in signal_assertions["headroom_guardrails"]:
                    bound_label = "lower bound" if item["bound"] == "min" else "upper bound"
                    lines.append(
                        "- `{status}` `{case_id}` {bound}: actual `{actual_headroom:.1f}` vs expected `>= {minimum:.1f}` within `{score_range}`".format(
                            status="PASS" if item["passed"] else "FAIL",
                            case_id=item["case_id"],
                            bound=bound_label,
                            actual_headroom=item["actual_headroom"],
                            minimum=item["minimum"],
                            score_range=item["expected_score_range"],
                        )
                    )
                    if item["reason"]:
                        lines.append(f"  - Reason: {item['reason']}")

    lines.extend([
        "",
        "## Industry Differentiation Summary",
        "",
        "| Profile | Cases | Avg Score | Min | Max | Span | Risk Distribution |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ])

    for item in summary["industry_differentiation_summary"]:
        risk_distribution = ", ".join(
            f"{level}={count}" for level, count in item["risk_distribution"].items()
        ) or "-"
        lines.append(
            "| {profile} | {cases} | {avg:.1f} | {minv:.1f} | {maxv:.1f} | {span:.1f} | {risk} |".format(
                profile=item["profile_id"],
                cases=item["case_count"],
                avg=item["average_score"],
                minv=item["min_score"],
                maxv=item["max_score"],
                span=item["score_span"],
                risk=risk_distribution,
            )
        )

    lines.extend(["", "## Case Results", ""])
    for row in results:
        expected = row["expected"]
        actual = row["actual"]
        checks = row["checks"]
        lines.extend(
            [
                f"### {row['case_id']} — {row['input']['company_name']}",
                "",
                f"- Industry/Profile: `{row['input']['industry']}` / `{actual['ruleset_profile_id']}`",
                f"- Score: expected `{expected['score_range'] or 'N/A'}` → actual `{actual['clean_core_score']:.1f}` ({_check_label(checks['score_range_hit'])})",
                f"- Risk: expected `{expected['risk_level'] or 'N/A'}` → actual `{actual['risk_level']}` ({_check_label(checks['risk_exact_match'])})",
                f"- Expected rules(any): `{', '.join(expected['rule_ids_any']) or '-'}` → matched `{', '.join(checks['matched_rule_ids']) or '-'}` ({_check_label(checks['rule_any_match'])})",
                f"- Expected recommendations(any): `{', '.join(expected['recommendation_ids_any']) or '-'}` → matched `{', '.join(checks['matched_recommendation_ids']) or '-'}` ({_check_label(checks['recommendation_any_match'])})",
                f"- Overall: `{_check_label(checks['all_expected_checks_passed'])}`",
            ]
        )
        if row["notes"]:
            lines.append(f"- Notes: {row['notes']}")
        if actual["resolution_warnings"]:
            lines.append(f"- Resolution warnings: {', '.join(actual['resolution_warnings'])}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def write_artifacts(
    *,
    fixture_path: Path,
    output_dir: Path,
    metadata: dict[str, Any],
    summary: dict[str, Any],
    results: list[dict[str, Any]],
) -> tuple[Path, Path, dict[str, Any]]:
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "demo_benchmark_eval.json"
    markdown_path = output_dir / "demo_benchmark_eval.md"

    payload = {
        "generated_at": generated_at,
        "fixture_path": _safe_relative(fixture_path),
        "metadata": metadata,
        "summary": summary,
        "results": results,
        "artifacts": {
            "json_path": _safe_relative(json_path),
            "markdown_path": _safe_relative(markdown_path),
        },
    }

    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(
        _build_markdown_report(
            generated_at=generated_at,
            fixture_path=fixture_path,
            summary=summary,
            results=results,
        ),
        encoding="utf-8",
    )
    return json_path, markdown_path, payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate deterministic demo benchmark cases.")
    parser.add_argument("--path", "--fixture", dest="path", default=str(DEFAULT_FIXTURE_PATH), help="benchmark fixture path")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="artifact output directory")
    parser.add_argument("--lang", default="ko", help="recommendation locale (default: ko)")
    parser.add_argument("--json", action="store_true", help="print JSON artifact payload to stdout")
    args = parser.parse_args()

    fixture_path = Path(args.path)
    output_dir = Path(args.output_dir)

    cases, metadata = load_benchmark_cases(fixture_path)
    results, summary = evaluate_cases(cases, lang=args.lang, metadata=metadata)
    json_path, markdown_path, payload = write_artifacts(
        fixture_path=fixture_path,
        output_dir=output_dir,
        metadata=metadata,
        summary=summary,
        results=results,
    )

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        benchmark_gate_passed = summary["benchmark_gate_passed"]
        print(f"[{'ok' if benchmark_gate_passed else 'fail'}] evaluated {summary['total_cases']} cases")
        print(f"- score range hit rate: {_format_rate(summary['metrics']['score_range_hit_rate'])}")
        print(f"- risk exact match rate: {_format_rate(summary['metrics']['risk_exact_match_rate'])}")
        print(f"- recommendation coverage rate: {_format_rate(summary['metrics']['recommendation_coverage_rate'])}")
        print(f"- signal assertion pass rate: {_format_rate(summary['metrics']['signal_assertion_pass_rate'])}")
        print(f"- benchmark gate: {'PASS' if benchmark_gate_passed else 'FAIL'}")
        print(
            "- score dispersion: span {span:.1f}, stddev {stddev:.1f}".format(
                span=summary["tuning_signals"]["score_distribution"]["span"],
                stddev=summary["tuning_signals"]["score_distribution"]["stddev"],
            )
        )
        closest_pair = summary["tuning_signals"]["closest_score_pairs"][0]
        print(
            "- closest score pair: {left} ↔ {right} (gap {gap:.1f})".format(
                left=closest_pair["left_case_id"],
                right=closest_pair["right_case_id"],
                gap=closest_pair["gap"],
            )
        )
        print(f"- json artifact: {_safe_relative(json_path)}")
        print(f"- markdown artifact: {_safe_relative(markdown_path)}")
    return 0 if summary["benchmark_gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
