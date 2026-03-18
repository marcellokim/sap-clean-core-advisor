"""Targeted tests for the Streamlit UI redesign foundation."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from ui import sidebar
from ui.styles import PRIMARY_FONT_STACK, STREAMLIT_SELECTOR_INVENTORY, build_global_styles
from ui.tabs import clean_core


class UiRedesignFoundationTests(unittest.TestCase):
    def test_global_styles_use_new_font_stack_and_shared_selectors(self) -> None:
        css = build_global_styles()

        self.assertIn(PRIMARY_FONT_STACK, css)
        self.assertNotIn("Inter", PRIMARY_FONT_STACK)
        self.assertIn(STREAMLIT_SELECTOR_INVENTORY["form"], css)
        self.assertIn(STREAMLIT_SELECTOR_INVENTORY["metric"], css)
        self.assertIn("--advisor-accent", css)

    def test_sidebar_copy_localizes_new_shell_language(self) -> None:
        with patch.object(sidebar.st, "session_state", {"ui_lang": "EN"}, create=True):
            copy_en = sidebar._sidebar_copy()

        self.assertEqual(copy_en["product_title"], "SAP Clean Core Advisor")
        self.assertEqual(copy_en["persona_title"], "Recommended scenario")
        self.assertIn("executive-ready", copy_en["product_summary"].lower())
        self.assertTrue(all("📦" not in item and "🏢" not in item for item in copy_en["value_items"]))

    def test_clean_core_empty_state_content_localizes_without_emoji_chrome(self) -> None:
        with patch.object(clean_core.st, "session_state", {"ui_lang": "KO"}, create=True):
            title_ko, description_ko, highlights_ko = clean_core._empty_state_content()
        with patch.object(clean_core.st, "session_state", {"ui_lang": "EN"}, create=True):
            title_en, description_en, highlights_en = clean_core._empty_state_content()

        self.assertEqual(title_ko, "분석 준비")
        self.assertEqual(title_en, "Prepare the assessment")
        self.assertEqual(len(highlights_ko), 4)
        self.assertEqual(len(highlights_en), 4)
        self.assertNotIn("👆", description_ko)
        self.assertNotIn("👆", description_en)

    def test_app_shell_source_uses_non_emoji_navigation_chrome(self) -> None:
        source = Path("app.py").read_text(encoding="utf-8")

        self.assertNotIn('page_icon="🏗️"', source)
        self.assertNotIn('_("🔍 Clean Core Assessment"', source)
        self.assertNotIn('_("🤖 Joule Readiness Checklist"', source)
        self.assertIn('return ["Clean Core Assessment", "Joule Readiness"]', source)


if __name__ == "__main__":
    unittest.main()
