"""UI style helpers for the Streamlit app shell."""

from __future__ import annotations

from collections.abc import Sequence
from html import escape

import streamlit as st

PRIMARY_FONT_STACK = '"Segoe UI", "Noto Sans KR", "Apple SD Gothic Neo", "Helvetica Neue", Arial, sans-serif'

THEME_TOKENS: dict[str, str] = {
    "accent": "#0A6ED1",
    "accent_dark": "#085CAF",
    "accent_soft": "#EAF3FF",
    "background": "#F4F7FB",
    "background_alt": "#EDF2F8",
    "surface": "#FFFFFF",
    "surface_alt": "#F8FAFC",
    "text": "#102A43",
    "muted": "#52606D",
    "line": "#D9E2EC",
    "shadow": "0 18px 45px rgba(15, 23, 42, 0.08)",
    "shadow_soft": "0 10px 24px rgba(15, 23, 42, 0.06)",
    "success": "#1F8A4C",
    "warning": "#B7791F",
    "danger": "#B42318",
}

STREAMLIT_SELECTOR_INVENTORY: dict[str, str] = {
    "main_block": ".stApp [data-testid=\"stAppViewContainer\"] > .main .block-container",
    "sidebar": "[data-testid=\"stSidebar\"]",
    "tabs_list": ".stTabs [data-baseweb=\"tab-list\"]",
    "tabs_tab": ".stTabs [data-baseweb=\"tab\"]",
    "form": 'div[data-testid="stForm"]',
    "border_wrapper": 'div[data-testid="stVerticalBlockBorderWrapper"]',
    "metric": 'div[data-testid="metric-container"]',
    "status": 'div[data-testid="stStatusWidget"]',
}


def build_global_styles() -> str:
    """Build the shared CSS foundation for the Streamlit UI."""
    tokens = THEME_TOKENS
    selectors = STREAMLIT_SELECTOR_INVENTORY

    return f"""
<style>
    :root {{
        --advisor-font: {PRIMARY_FONT_STACK};
        --advisor-accent: {tokens['accent']};
        --advisor-accent-dark: {tokens['accent_dark']};
        --advisor-accent-soft: {tokens['accent_soft']};
        --advisor-bg: {tokens['background']};
        --advisor-bg-alt: {tokens['background_alt']};
        --advisor-surface: {tokens['surface']};
        --advisor-surface-alt: {tokens['surface_alt']};
        --advisor-text: {tokens['text']};
        --advisor-muted: {tokens['muted']};
        --advisor-line: {tokens['line']};
        --advisor-shadow: {tokens['shadow']};
        --advisor-shadow-soft: {tokens['shadow_soft']};
        --advisor-success: {tokens['success']};
        --advisor-warning: {tokens['warning']};
        --advisor-danger: {tokens['danger']};
    }}

    html, body, [class*="css"] {{
        font-family: var(--advisor-font) !important;
        color: var(--advisor-text);
    }}

    .stApp {{
        background: linear-gradient(180deg, var(--advisor-bg) 0%, var(--advisor-bg-alt) 100%);
        color: var(--advisor-text);
    }}

    {selectors['main_block']} {{
        max-width: 1180px;
        padding-top: 2.5rem;
        padding-right: 2rem;
        padding-bottom: 3rem;
        padding-left: 2rem;
    }}

    {selectors['sidebar']} {{
        background: rgba(255, 255, 255, 0.94);
        border-right: 1px solid var(--advisor-line);
    }}

    {selectors['sidebar']} .block-container {{
        padding-top: 1.5rem;
        padding-right: 1.1rem;
        padding-bottom: 2rem;
        padding-left: 1.1rem;
    }}

    h1, h2, h3 {{
        color: var(--advisor-text);
        letter-spacing: -0.02em;
    }}

    h1 {{
        background: none !important;
        -webkit-background-clip: initial !important;
        -webkit-text-fill-color: initial !important;
        font-size: 2.35rem !important;
        font-weight: 700 !important;
        line-height: 1.1;
        padding-bottom: 0 !important;
    }}

    h2 {{
        font-size: 1.55rem !important;
        font-weight: 650 !important;
    }}

    h3 {{
        font-size: 1.08rem !important;
        font-weight: 650 !important;
    }}

    p, li, label, .stCaption, small {{
        color: var(--advisor-muted);
    }}

    {selectors['tabs_list']} {{
        gap: 0.65rem;
        padding: 0.4rem;
        border: 1px solid var(--advisor-line);
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.88);
        box-shadow: var(--advisor-shadow-soft);
    }}

    {selectors['tabs_tab']} {{
        min-height: 2.75rem;
        padding: 0.65rem 1.15rem;
        border-radius: 999px;
        color: var(--advisor-muted);
        font-weight: 600;
        transition: background 0.2s ease, color 0.2s ease, transform 0.2s ease;
    }}

    .stTabs [aria-selected="true"] {{
        background: var(--advisor-accent-soft) !important;
        color: var(--advisor-accent) !important;
        box-shadow: inset 0 0 0 1px rgba(10, 110, 209, 0.18);
    }}

    {selectors['form']} {{
        background: rgba(255, 255, 255, 0.92);
        border: 1px solid var(--advisor-line);
        border-radius: 26px;
        padding: 1rem 1.25rem 1.5rem;
        box-shadow: var(--advisor-shadow);
    }}

    {selectors['form']} {selectors['border_wrapper']} {{
        background: var(--advisor-surface-alt);
        border: 1px solid var(--advisor-line);
        border-radius: 22px;
        padding: 1rem 1.15rem;
        box-shadow: none;
    }}

    {selectors['border_wrapper']} > div {{
        gap: 0.75rem;
    }}

    {selectors['metric']} {{
        background: rgba(255, 255, 255, 0.96);
        border: 1px solid var(--advisor-line);
        border-radius: 20px;
        padding: 1rem 1.1rem !important;
        box-shadow: var(--advisor-shadow-soft);
        border-left: 4px solid var(--advisor-accent);
    }}

    {selectors['metric']} label {{
        color: var(--advisor-muted) !important;
        font-weight: 600 !important;
        font-size: 0.82rem !important;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }}

    {selectors['metric']} div[data-testid="stMetricValue"] {{
        color: var(--advisor-text);
        font-size: 1.7rem;
        font-weight: 700;
    }}

    [data-testid="stSelectbox"] label,
    [data-testid="stTextInput"] label,
    [data-testid="stNumberInput"] label,
    [data-testid="stMultiSelect"] label,
    [data-testid="stSlider"] label,
    [data-testid="stTextArea"] label {{
        font-size: 0.82rem !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: var(--advisor-muted) !important;
    }}

    [data-baseweb="select"] > div,
    [data-baseweb="input"] > div,
    [data-testid="stTextInput"] input,
    [data-testid="stNumberInput"] input,
    textarea {{
        border-radius: 14px !important;
        border-color: var(--advisor-line) !important;
        background: rgba(255, 255, 255, 0.98) !important;
        box-shadow: none !important;
    }}

    textarea {{
        min-height: 7rem;
    }}

    [data-baseweb="select"] > div:focus-within,
    [data-baseweb="input"] > div:focus-within,
    [data-testid="stTextInput"] input:focus,
    [data-testid="stNumberInput"] input:focus,
    textarea:focus {{
        border-color: var(--advisor-accent) !important;
        box-shadow: 0 0 0 1px rgba(10, 110, 209, 0.15) !important;
    }}

    .stButton > button,
    .stDownloadButton > button,
    div[data-testid="stFormSubmitButton"] button {{
        border: 0 !important;
        border-radius: 999px !important;
        min-height: 2.9rem;
        font-weight: 650 !important;
        background: var(--advisor-accent) !important;
        color: #ffffff !important;
        box-shadow: 0 12px 26px rgba(10, 110, 209, 0.18);
        transition: transform 0.18s ease, box-shadow 0.18s ease, background 0.18s ease;
    }}

    .stButton > button:hover,
    .stDownloadButton > button:hover,
    div[data-testid="stFormSubmitButton"] button:hover {{
        background: var(--advisor-accent-dark) !important;
        transform: translateY(-1px);
        box-shadow: 0 16px 28px rgba(10, 110, 209, 0.22);
    }}

    .stButton > button:focus,
    .stDownloadButton > button:focus,
    div[data-testid="stFormSubmitButton"] button:focus {{
        box-shadow: 0 0 0 3px rgba(10, 110, 209, 0.18) !important;
    }}

    div[data-testid="stAlert"] {{
        border-radius: 18px;
        border: 1px solid var(--advisor-line);
        box-shadow: var(--advisor-shadow-soft);
    }}

    {selectors['status']} {{
        border: 1px solid var(--advisor-line);
        border-radius: 20px;
        background: rgba(255, 255, 255, 0.94);
        box-shadow: var(--advisor-shadow-soft);
    }}

    .advisor-shell {{
        background: rgba(255, 255, 255, 0.94);
        border: 1px solid var(--advisor-line);
        border-radius: 28px;
        padding: 2rem 2.2rem;
        box-shadow: var(--advisor-shadow);
        margin-bottom: 1.75rem;
    }}

    .advisor-shell__eyebrow,
    .advisor-section-heading__eyebrow {{
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: var(--advisor-accent);
        margin-bottom: 0.55rem;
    }}

    .advisor-shell__title {{
        margin: 0;
        color: var(--advisor-text);
    }}

    .advisor-shell__description,
    .advisor-section-heading__description,
    .advisor-empty-state__description {{
        margin: 0.55rem 0 0;
        max-width: 50rem;
        font-size: 1rem;
        line-height: 1.65;
        color: var(--advisor-muted);
    }}

    .advisor-chip-row {{
        display: flex;
        flex-wrap: wrap;
        gap: 0.65rem;
        margin-top: 1rem;
    }}

    .advisor-chip {{
        display: inline-flex;
        align-items: center;
        min-height: 2rem;
        padding: 0.35rem 0.8rem;
        border-radius: 999px;
        background: var(--advisor-accent-soft);
        color: var(--advisor-accent);
        font-size: 0.88rem;
        font-weight: 600;
    }}

    .advisor-section-heading {{
        margin-bottom: 1rem;
    }}

    .advisor-section-heading__title,
    .advisor-empty-state__title {{
        margin: 0;
        color: var(--advisor-text);
    }}

    .advisor-empty-state {{
        margin-top: 1rem;
        padding: 1.5rem 1.6rem;
        border-radius: 26px;
        border: 1px solid var(--advisor-line);
        background: linear-gradient(180deg, rgba(255, 255, 255, 0.96) 0%, rgba(234, 243, 255, 0.78) 100%);
        box-shadow: var(--advisor-shadow-soft);
    }}

    .advisor-empty-state__list,
    .advisor-muted-list {{
        margin: 0.85rem 0 0;
        padding-left: 1.1rem;
    }}

    .advisor-empty-state__list li {{
        color: var(--advisor-text);
        margin-bottom: 0.3rem;
    }}

    .advisor-muted-list li {{
        color: var(--advisor-muted);
        margin-bottom: 0.3rem;
    }}

    .advisor-form-note {{
        margin-top: 0.85rem;
        font-size: 0.92rem;
        color: var(--advisor-muted);
    }}

    .advisor-badge-row {{
        display: flex;
        flex-wrap: wrap;
        gap: 0.6rem;
        margin-top: 0.85rem;
    }}

    .advisor-badge {{
        display: inline-flex;
        align-items: center;
        min-height: 2rem;
        padding: 0.35rem 0.8rem;
        border-radius: 999px;
        font-size: 0.84rem;
        font-weight: 650;
        border: 1px solid transparent;
    }}

    .advisor-badge--neutral {{
        background: rgba(16, 42, 67, 0.06);
        border-color: rgba(16, 42, 67, 0.08);
        color: var(--advisor-text);
    }}

    .advisor-badge--high {{
        background: rgba(180, 35, 24, 0.1);
        border-color: rgba(180, 35, 24, 0.16);
        color: var(--advisor-danger);
    }}

    .advisor-badge--medium {{
        background: rgba(183, 121, 31, 0.1);
        border-color: rgba(183, 121, 31, 0.18);
        color: var(--advisor-warning);
    }}

    .advisor-badge--low {{
        background: rgba(31, 138, 76, 0.1);
        border-color: rgba(31, 138, 76, 0.16);
        color: var(--advisor-success);
    }}

    .advisor-note-card {{
        padding: 1rem 1.1rem;
        border-radius: 18px;
        border: 1px solid var(--advisor-line);
        background: rgba(248, 250, 252, 0.92);
    }}

    .advisor-note-card__label {{
        display: block;
        margin-bottom: 0.35rem;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--advisor-accent);
    }}

    .advisor-note-card__body {{
        margin: 0;
        color: var(--advisor-text);
        line-height: 1.65;
    }}

    .advisor-list-tight {{
        margin: 0;
        padding-left: 1.1rem;
    }}

    .advisor-list-tight li {{
        color: var(--advisor-text);
        margin-bottom: 0.35rem;
    }}

    @media (max-width: 991px) {{
        {selectors['main_block']} {{
            padding-right: 1rem;
            padding-left: 1rem;
        }}

        .advisor-shell {{
            padding: 1.5rem;
        }}
    }}
</style>
"""


def apply_global_styles() -> None:
    """Apply global Streamlit style overrides."""
    st.markdown(build_global_styles(), unsafe_allow_html=True)


def render_shell_header(
    *,
    eyebrow: str,
    title: str,
    description: str,
    highlights: Sequence[str] | None = None,
) -> None:
    """Render the app-level enterprise shell header."""
    chips = ""
    if highlights:
        chip_markup = "".join(
            f"<span class=\"advisor-chip\">{escape(item)}</span>" for item in highlights
        )
        chips = f"<div class=\"advisor-chip-row\">{chip_markup}</div>"

    st.markdown(
        f"""
        <section class="advisor-shell">
            <div class="advisor-shell__eyebrow">{escape(eyebrow)}</div>
            <h1 class="advisor-shell__title">{escape(title)}</h1>
            <p class="advisor-shell__description">{escape(description)}</p>
            {chips}
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_section_heading(*, eyebrow: str, title: str, description: str | None = None) -> None:
    """Render a reusable section heading."""
    description_markup = ""
    if description:
        description_markup = (
            f"<p class=\"advisor-section-heading__description\">{escape(description)}</p>"
        )

    st.markdown(
        f"""
        <div class="advisor-section-heading">
            <div class="advisor-section-heading__eyebrow">{escape(eyebrow)}</div>
            <h3 class="advisor-section-heading__title">{escape(title)}</h3>
            {description_markup}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_empty_state_panel(*, title: str, description: str, highlights: Sequence[str]) -> None:
    """Render a consistent empty-state panel."""
    highlight_markup = "".join(
        f"<li>{escape(item)}</li>" for item in highlights
    )
    st.markdown(
        f"""
        <section class="advisor-empty-state">
            <h3 class="advisor-empty-state__title">{escape(title)}</h3>
            <p class="advisor-empty-state__description">{escape(description)}</p>
            <ul class="advisor-empty-state__list">{highlight_markup}</ul>
        </section>
        """,
        unsafe_allow_html=True,
    )


def status_badge_markup(*, label: str, value: str, tone: str = "neutral") -> str:
    """Return reusable badge markup for risk and mode indicators."""
    normalized_tone = tone if tone in {"neutral", "high", "medium", "low"} else "neutral"
    return (
        f"<span class=\"advisor-badge advisor-badge--{normalized_tone}\">"
        f"{escape(label)}: {escape(value)}"
        "</span>"
    )
