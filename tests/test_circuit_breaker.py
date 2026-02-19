"""Tests for circuit breaker behavior."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from services.infrastructure.policy.circuit_breaker import CircuitBreaker


class CircuitBreakerTests(unittest.TestCase):
    def test_open_after_threshold_failures(self) -> None:
        cb = CircuitBreaker(failure_threshold=2, open_seconds=60)
        self.assertTrue(cb.can_execute())
        cb.record_failure()
        self.assertTrue(cb.can_execute())
        cb.record_failure()
        self.assertFalse(cb.can_execute())
        self.assertEqual(cb.snapshot().state, "open")

    def test_half_open_and_recovery(self) -> None:
        cb = CircuitBreaker(failure_threshold=1, open_seconds=10)
        with patch("time.time", return_value=100.0):
            cb.record_failure()
            self.assertFalse(cb.can_execute())
        with patch("time.time", return_value=111.0):
            self.assertTrue(cb.can_execute())  # half-open probe allowed
            self.assertEqual(cb.snapshot().state, "half_open")
            cb.record_success()
            self.assertTrue(cb.can_execute())
            self.assertEqual(cb.snapshot().state, "closed")


if __name__ == "__main__":
    unittest.main()

