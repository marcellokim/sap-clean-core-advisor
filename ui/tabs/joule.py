"""Joule checklist tab rendering and handler wiring."""

from __future__ import annotations

import streamlit as st

from services.domain.joule_readiness_engine import generate_joule_gap_analysis
from ui.joule_checklist import render_joule_checklist
from ui.locales import _

RISK_COLORS = {"High": "#BB0000", "Medium": "#E76500", "Low": "#36A41D"}


def handle_gap_analysis(checked: list[str], unchecked: list[str]) -> None:
    """Generate and render the Joule gap analysis report."""

    status_msg = _(
        "🧠 AI가 Gap Analysis 리포트를 작성 중입니다...",
        "🧠 AI is compiling the Gap Analysis Report...",
    )
    with st.status(status_msg, expanded=True) as status:
        st.write(_("고객 데이터 룰셋 매핑 중...", "Mapping customer data to rulesets..."))
        result = generate_joule_gap_analysis(checked, unchecked)
        status.update(label=_("✅ 분석 완료!", "✅ Analysis Complete!"), state="complete", expanded=False)

        st.markdown("---")
        st.subheader(
            _("📊 Joule Readiness Gap Analysis 리포트", "📊 Joule Readiness Gap Analysis Report")
        )

        color = RISK_COLORS.get(result.risk_level, "#36A41D")
        st.markdown(
            f"<div style='margin-bottom: 12px;'>"
            f"<span style='background:{color}; color:white; padding:4px 12px; "
            f"border-radius:12px; font-weight:bold;'>"
            + _("리스크 수준: ", "Risk Level: ")
            + f"{result.risk_level}</span></div>",
            unsafe_allow_html=True,
        )

        st.markdown(f"**Executive Summary:**\n{result.executive_summary}\n")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**🚨 식별된 결함 (Identified Gaps):**")
            for gap in result.identified_gaps:
                st.markdown(f"- {gap}")
        with col2:
            st.markdown("**🛠️ 조치 권고 (Recommended Actions):**")
            for action in result.recommended_actions:
                st.markdown(f"- {action}")


def render_joule_tab() -> None:
    """Render the Joule checklist tab with its analysis callback."""

    render_joule_checklist(handle_gap_analysis)
