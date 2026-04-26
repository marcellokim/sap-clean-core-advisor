"""Tests for analysis pipeline timing helpers."""

from __future__ import annotations

import time
import unittest

from services.application.pipeline_timing import remaining_timeout_sec, timeout_hit


class PipelineTimingTests(unittest.TestCase):
    def test_disabled_timeout_never_hits(self) -> None:
        start = time.perf_counter()

        self.assertFalse(timeout_hit(start, 0))
        self.assertIsNone(remaining_timeout_sec(start, 0))

    def test_elapsed_timeout_reports_zero_remaining_budget(self) -> None:
        start = time.perf_counter() - 1.0

        self.assertTrue(timeout_hit(start, 1))
        self.assertEqual(remaining_timeout_sec(start, 1), 0.0)


if __name__ == "__main__":
    unittest.main()
