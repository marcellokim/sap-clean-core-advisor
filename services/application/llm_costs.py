"""LLM usage/cost calculation helpers."""

from __future__ import annotations

from config.settings import settings
from services.llm_provider import LLMUsage


def usage_tokens_map(usage: LLMUsage) -> dict[str, int]:
    return {
        "prompt_tokens": max(0, int(usage.prompt_tokens)),
        "output_tokens": max(0, int(usage.output_tokens)),
        "total_tokens": max(0, int(usage.total_tokens)),
    }


def estimate_llm_cost_usd(usage: LLMUsage) -> float:
    prompt_cost = (max(0, usage.prompt_tokens) / 1_000_000) * settings.LLM_PRICE_INPUT_PER_1M
    output_cost = (max(0, usage.output_tokens) / 1_000_000) * settings.LLM_PRICE_OUTPUT_PER_1M
    return round(prompt_cost + output_cost, 8)


def monthly_llm_projection_usd(cost_per_request_usd: float) -> dict[str, float]:
    monthly_requests = max(0.0, float(settings.LLM_MONTHLY_REQUESTS))
    return {
        "monthly_requests": round(monthly_requests, 2),
        "estimated_usd": round(cost_per_request_usd * monthly_requests, 4),
    }
