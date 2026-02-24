import streamlit as st

def _(ko_text: str, en_text: str) -> str:
    """Return English text if ui_lang is EN, else Korean text."""
    lang = st.session_state.get("ui_lang", "KO")
    return en_text if lang == "EN" else ko_text
