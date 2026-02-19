"""LLM token usage normalization and Gemini cost estimation helpers."""

from __future__ import annotations

import json
import os
from math import ceil
from typing import Any

from services.llm_provider import LLMUsage, ReportPayload

DEFAULT_MODEL = "gemini-2.0-flash-lite"
DEFAULT_INPUT_PRICE_PER_1M = 0.075
DEFAULT_OUTPUT_PRICE_PER_1M = 0.30


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = float(raw)
    except ValueError:
        return default
    return max(0.0, value)


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(1, value)


def estimate_tokens_from_text(text: str) -> int:
    """Rough token estimator based on character count."""
    if not text:
        return 0
    divisor = _env_int("LLM_TOKEN_ESTIMATE_CHAR_DIVISOR", 4)
    return max(1, ceil(len(text) / divisor))


def _to_int(value: Any) -> int:
    try:
        return max(0, int(value))
    except Exception:
        return 0


def normalize_usage_metadata(raw_usage: dict[str, Any] | None) -> LLMUsage:
    """Normalize usage keys from provider metadata variants."""
    usage = raw_usage or {}
    prompt_tokens = _to_int(
        usage.get("input_tokens")
        or usage.get("prompt_tokens")
        or usage.get("prompt_token_count")
        or usage.get("input_token_count")
    )
    output_tokens = _to_int(
        usage.get("output_tokens")
        or usage.get("candidate_tokens")
        or usage.get("candidates_token_count")
        or usage.get("completion_tokens")
        or usage.get("output_token_count")
    )
    total_tokens = _to_int(
        usage.get("total_tokens")
        or usage.get("total_token_count")
    )
    if total_tokens <= 0:
        total_tokens = prompt_tokens + output_tokens
    return LLMUsage(
        prompt_tokens=prompt_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        source="provider" if total_tokens > 0 else "none",
    )


def estimate_usage_from_payload(payload: ReportPayload, output_text: str) -> LLMUsage:
    """Estimate token usage from payload text when provider usage is unavailable."""
    prompt_text = json.dumps(
        {
            "customer_info": payload.customer_info,
            "clean_core_score": payload.clean_core_score,
            "score_breakdown": payload.score_breakdown,
            "current_tco": payload.current_tco,
            "projected_tco": payload.projected_tco,
            "savings_3yr": payload.savings_3yr,
            "risk_level": payload.risk_level,
            "risk_factors": payload.risk_factors,
            "tech_debt": payload.tech_debt,
            "recommendations": payload.recommendations,
            "rag_context": payload.rag_context,
        },
        ensure_ascii=False,
    )
    prompt_tokens = estimate_tokens_from_text(prompt_text)
    output_tokens = estimate_tokens_from_text(output_text)
    return LLMUsage(
        prompt_tokens=prompt_tokens,
        output_tokens=output_tokens,
        total_tokens=prompt_tokens + output_tokens,
        source="estimated",
    )


def estimate_usage_from_inputs(inputs: dict[str, Any], output_text: str) -> LLMUsage:
    """Estimate usage for per-chain calls using formatted input dict."""
    prompt_tokens = estimate_tokens_from_text(json.dumps(inputs, ensure_ascii=False))
    output_tokens = estimate_tokens_from_text(output_text)
    return LLMUsage(
        prompt_tokens=prompt_tokens,
        output_tokens=output_tokens,
        total_tokens=prompt_tokens + output_tokens,
        source="estimated",
    )


def get_model_prices(model: str | None = None) -> tuple[float, float]:
    """Return input/output USD prices per 1M tokens."""
    selected_model = (model or os.getenv("GEMINI_MODEL", DEFAULT_MODEL)).strip().lower()
    default_input = DEFAULT_INPUT_PRICE_PER_1M
    default_output = DEFAULT_OUTPUT_PRICE_PER_1M

    # model-specific override env keys
    model_key = selected_model.upper().replace("-", "_").replace(".", "_")
    input_price = _env_float(
        f"LLM_PRICE_{model_key}_INPUT_PER_1M",
        _env_float("LLM_PRICE_INPUT_PER_1M", default_input),
    )
    output_price = _env_float(
        f"LLM_PRICE_{model_key}_OUTPUT_PER_1M",
        _env_float("LLM_PRICE_OUTPUT_PER_1M", default_output),
    )
    return input_price, output_price


def estimate_cost_usd(usage: LLMUsage, model: str | None = None) -> float:
    """Estimate per-run USD cost from token usage."""
    input_price, output_price = get_model_prices(model)
    return round(
        (usage.prompt_tokens / 1_000_000) * input_price
        + (usage.output_tokens / 1_000_000) * output_price,
        8,
    )


def build_monthly_projection(cost_per_run_usd: float) -> dict[str, float]:
    """Build simple monthly cost projection table."""
    baseline_requests = [100, 500, 1_000, 5_000, 10_000]
    env_requests = _env_int("LLM_MONTHLY_REQUESTS", 1000)
    if env_requests not in baseline_requests:
        baseline_requests.append(env_requests)
    baseline_requests = sorted(set(baseline_requests))

    projection: dict[str, float] = {}
    for requests in baseline_requests:
        projection[f"{requests}_runs"] = round(cost_per_run_usd * requests, 6)
    return projection

