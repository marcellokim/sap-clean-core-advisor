"""Tests for UI-level analysis policy lock."""

from __future__ import annotations

import unittest

from config.settings import settings
from ui.policy import get_locked_analysis_policy


class AppPolicyLockTests(unittest.TestCase):
    def test_ui_policy_is_always_hybrid(self) -> None:
        old_mode = settings.ANALYSIS_MODE
        try:
            settings.ANALYSIS_MODE = "deterministic"
            policy = get_locked_analysis_policy()
            self.assertEqual(policy.analysis_mode, "hybrid")

            settings.ANALYSIS_MODE = "llm_only"
            policy = get_locked_analysis_policy()
            self.assertEqual(policy.analysis_mode, "hybrid")
        finally:
            settings.ANALYSIS_MODE = old_mode


if __name__ == "__main__":
    unittest.main()

