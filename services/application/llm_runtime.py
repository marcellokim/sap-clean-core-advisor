"""LLM runtime execution helpers."""

from __future__ import annotations

import concurrent.futures
from typing import Callable

from services.llm_provider import LLMProvider, ReportPayload, ReportSections


def generate_with_optional_timeout(
    provider: LLMProvider,
    payload: ReportPayload,
    timeout_seconds_getter: Callable[[], float | None],
) -> ReportSections:
    remaining_timeout = timeout_seconds_getter()
    if remaining_timeout is None:
        return provider.generate_report(payload)

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = executor.submit(provider.generate_report, payload)
    try:
        return future.result(timeout=remaining_timeout)
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
