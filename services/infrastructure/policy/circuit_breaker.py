"""Simple in-memory circuit breaker for external dependency protection."""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass(frozen=True)
class CircuitState:
    """Circuit breaker runtime state snapshot."""

    state: str  # closed | open | half_open
    failure_count: int
    opened_at_unix: float | None


class CircuitBreaker:
    """In-memory circuit breaker with half-open probing."""

    def __init__(self, failure_threshold: int = 3, open_seconds: int = 120) -> None:
        self.failure_threshold = max(1, int(failure_threshold))
        self.open_seconds = max(1, int(open_seconds))
        self._state = "closed"
        self._failure_count = 0
        self._opened_at: float | None = None

    def _now(self) -> float:
        return time.time()

    def can_execute(self) -> bool:
        """Return whether external call should be attempted."""
        if self._state == "closed":
            return True
        if self._state == "open":
            if self._opened_at is None:
                self._state = "half_open"
                return True
            if (self._now() - self._opened_at) >= self.open_seconds:
                self._state = "half_open"
                return True
            return False
        # half_open
        return True

    def record_success(self) -> None:
        """Close circuit after successful probe/call."""
        self._state = "closed"
        self._failure_count = 0
        self._opened_at = None

    def record_failure(self) -> None:
        """Increment failures and open circuit when threshold reached."""
        self._failure_count += 1
        if self._state == "half_open" or self._failure_count >= self.failure_threshold:
            self._state = "open"
            self._opened_at = self._now()

    def snapshot(self) -> CircuitState:
        return CircuitState(
            state=self._state,
            failure_count=self._failure_count,
            opened_at_unix=self._opened_at,
        )

