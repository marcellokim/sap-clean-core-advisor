"""Tab-level UI entry points for the Streamlit app."""

from __future__ import annotations


def render_clean_core_tab() -> None:
    from ui.tabs.clean_core import render_clean_core_tab as impl

    impl()


def render_joule_tab() -> None:
    from ui.tabs.joule import render_joule_tab as impl

    impl()

__all__ = ["render_clean_core_tab", "render_joule_tab"]
