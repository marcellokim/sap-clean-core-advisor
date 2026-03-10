"""Tab-level UI entry points for the Streamlit app."""

from ui.tabs.clean_core import render_clean_core_tab
from ui.tabs.joule import render_joule_tab

__all__ = ["render_clean_core_tab", "render_joule_tab"]
