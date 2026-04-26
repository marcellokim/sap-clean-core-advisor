"""Small timing helpers for policy-driven analysis stages."""

from __future__ import annotations

import time


def elapsed_ms(start_ts: float) -> int:
    """Return elapsed milliseconds from a perf_counter timestamp."""
    return max(0, int((time.perf_counter() - start_ts) * 1000))


def timeout_hit(start_ts: float, timeout_ms: int) -> bool:
    """Return whether the configured timeout budget has been exhausted."""
    if timeout_ms <= 0:
        return False
    return elapsed_ms(start_ts) >= timeout_ms


def remaining_timeout_sec(start_ts: float, timeout_ms: int) -> float | None:
    """Return remaining timeout budget in seconds, or None when disabled."""
    if timeout_ms <= 0:
        return None
    remaining_ms = timeout_ms - elapsed_ms(start_ts)
    if remaining_ms <= 0:
        return 0.0
    return remaining_ms / 1000.0
