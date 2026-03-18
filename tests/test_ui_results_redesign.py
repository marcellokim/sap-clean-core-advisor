"""Targeted tests for the redesigned dashboard and Joule result surfaces."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

import ui.joule_checklist as joule_checklist
from ui.tabs import joule


class UiResultsRedesignTests(unittest.TestCase):
    def test_dashboard_source_removes_inline_metric_css_and_emoji_labels(self) -> None:
        source = Path("ui/dashboard.py").read_text(encoding="utf-8")

        self.assertNotIn('div[data-testid="metric-container"] {', source)
        self.assertNotIn("🏆", source)
        self.assertNotIn("📉", source)
        self.assertNotIn("💰", source)
        self.assertIn("Core KPIs", source)

    def test_joule_checklist_copy_localizes_sections(self) -> None:
        with patch.object(joule_checklist.st, "session_state", {"ui_lang": "EN"}, create=True):
            copy_en = joule_checklist._checklist_copy()
            sections_en = joule_checklist._checklist_sections()

        self.assertEqual(copy_en["title"], "SAP Joule readiness checklist")
        self.assertEqual(copy_en["completion_label"], "Completion")
        self.assertEqual(sections_en[0]["title"], "Prerequisites")
        self.assertEqual(sum(len(section["items"]) for section in sections_en), 12)
        self.assertTrue(all("🤖" not in section["title"] for section in sections_en))

    def test_joule_gap_analysis_copy_is_deemoji(self) -> None:
        with patch.object(joule.st, "session_state", {"ui_lang": "EN"}, create=True):
            copy_en = joule._gap_analysis_copy()

        self.assertEqual(copy_en["title"], "Joule readiness gap analysis")
        self.assertNotIn("🧠", copy_en["status"])
        self.assertNotIn("📊", copy_en["title"])
        self.assertEqual(copy_en["summary_title"], "Executive summary")


if __name__ == "__main__":
    unittest.main()
