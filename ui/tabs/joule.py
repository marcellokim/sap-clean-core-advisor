"""Joule checklist tab rendering and handler wiring."""

from __future__ import annotations

from html import escape

import streamlit as st

from services.domain.joule_readiness_engine import generate_joule_gap_analysis
from ui.joule_checklist import render_joule_checklist
from ui.locales import _
from ui.styles import render_section_heading, status_badge_markup

RISK_TONES = {"High": "high", "Medium": "medium", "Low": "low"}


def _gap_analysis_copy() -> dict[str, str]:
    """Return localized copy for the Joule gap analysis surface."""
    return {
        "status": _(
            "AI가 Joule readiness gap analysis를 작성하고 있습니다...",
            "AI is drafting the Joule readiness gap analysis...",
        ),
        "working": _(
            "체크리스트 응답을 바탕으로 준비 수준을 정리하고 있습니다...",
            "Organizing readiness findings from the checklist responses...",
        ),
        "complete": _("분석 완료", "Analysis complete"),
        "eyebrow": "Gap analysis",
        "title": _("Joule readiness gap analysis", "Joule readiness gap analysis"),
        "description": _(
            "미체크 항목을 기반으로 우선순위와 실행 조치를 정리했습니다.",
            "The unchecked items are converted into prioritized gaps and recommended actions.",
        ),
        "summary_title": _("Executive summary", "Executive summary"),
        "gaps_title": _("식별된 결함", "Identified gaps"),
        "actions_title": _("권고 조치", "Recommended actions"),
        "no_gaps": _("현재 식별된 추가 결함이 없습니다.", "No additional gaps were identified."),
        "no_actions": _("현재 추가 권고 조치가 없습니다.", "No additional actions are required."),
        "risk_label": _("리스크", "Risk"),
    }


def _render_html_list(items: list[str]) -> str:
    return "<ul class='advisor-list-tight'>" + "".join(f"<li>{escape(item)}</li>" for item in items) + "</ul>"


def handle_gap_analysis(checked: list[str], unchecked: list[str]) -> None:
    """Generate and render the Joule gap analysis report."""
    copy = _gap_analysis_copy()

    with st.status(copy["status"], expanded=True) as status:
        st.write(copy["working"])
        result = generate_joule_gap_analysis(checked, unchecked)
        status.update(label=copy["complete"], state="complete", expanded=False)

        with st.container(border=True):
            render_section_heading(
                eyebrow=copy["eyebrow"],
                title=copy["title"],
                description=copy["description"],
            )
            st.markdown(
                "<div class='advisor-badge-row'>"
                + status_badge_markup(
                    label=copy["risk_label"],
                    value=result.risk_level,
                    tone=RISK_TONES.get(result.risk_level, "neutral"),
                )
                + "</div>",
                unsafe_allow_html=True,
            )
            st.markdown(
                "<div class='advisor-note-card'>"
                f"<span class='advisor-note-card__label'>{escape(copy['summary_title'])}</span>"
                f"<p class='advisor-note-card__body'>{escape(result.executive_summary)}</p>"
                "</div>",
                unsafe_allow_html=True,
            )

        col1, col2 = st.columns(2)
        with col1:
            with st.container(border=True):
                render_section_heading(
                    eyebrow="Gaps",
                    title=copy["gaps_title"],
                    description=_(
                        "준비가 미흡한 항목을 먼저 정리했습니다.",
                        "The gaps highlight where prerequisite readiness is incomplete.",
                    ),
                )
                if result.identified_gaps:
                    st.markdown(_render_html_list(result.identified_gaps), unsafe_allow_html=True)
                else:
                    st.caption(copy["no_gaps"])
        with col2:
            with st.container(border=True):
                render_section_heading(
                    eyebrow="Actions",
                    title=copy["actions_title"],
                    description=_(
                        "바로 이어서 실행할 권고 조치를 제시합니다.",
                        "These are the recommended next actions to close the gaps.",
                    ),
                )
                if result.recommended_actions:
                    st.markdown(_render_html_list(result.recommended_actions), unsafe_allow_html=True)
                else:
                    st.caption(copy["no_actions"])


def render_joule_tab() -> None:
    """Render the Joule checklist tab with its analysis callback."""
    render_joule_checklist(handle_gap_analysis)
