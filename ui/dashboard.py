"""결과 대시보드 (Streamlit + Plotly).

Clean Core Score 게이지, 기술 부채 히트맵, TCO 비교 차트,
리스크 요인, Executive Summary, PDF 다운로드를 포함합니다.
"""

from __future__ import annotations

import streamlit as st
import plotly.graph_objects as go

from models.schemas import AdvisorOutput, CustomerInput
from ui.locales import _

# ────────────────────────────────────────────────────────────────────
# 색상 팔레트 (SAP 톤)
# ────────────────────────────────────────────────────────────────────
SAP_BLUE = "#0070F2"
SAP_DARK = "#1B2559"
SAP_GREEN = "#36A41D"
SAP_ORANGE = "#E76500"
SAP_RED = "#BB0000"

RISK_COLORS = {"High": SAP_RED, "Medium": SAP_ORANGE, "Low": SAP_GREEN}


def _format_b_krw(value: float) -> str:
    """Format billion-KRW values with enough precision to surface small differences."""
    return f"{value:.2f}" if abs(value) < 10 else f"{value:.1f}"


def _render_score_gauge(score: float) -> go.Figure:
    """Clean Core Score 게이지 차트."""
    if score >= 70:
        bar_color = SAP_GREEN
    elif score >= 40:
        bar_color = SAP_ORANGE
    else:
        bar_color = SAP_RED

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={"suffix": " / 100", "font": {"size": 28}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1},
            "bar": {"color": bar_color, "thickness": 0.75},
            "steps": [
                {"range": [0, 30], "color": "#FFEBEE"},
                {"range": [30, 60], "color": "#FFF3E0"},
                {"range": [60, 100], "color": "#E8F5E9"},
            ],
            "threshold": {
                "line": {"color": SAP_DARK, "width": 3},
                "thickness": 0.8,
                "value": score,
            },
        },
        title={"text": "Clean Core Score", "font": {"size": 16}},
    ))
    fig.update_layout(height=280, margin=dict(t=60, b=20, l=30, r=30))
    return fig


def _render_score_breakdown(breakdown: dict[str, float]) -> go.Figure:
    """항목별 점수 레이더 차트."""
    labels_map_ko = {
        "custom_code": "커스텀 코드",
        "erp_version": "ERP 버전",
        "database": "데이터베이스",
        "module_complexity": "모듈 복잡도",
    }
    labels_map_en = {
        "custom_code": "Custom Code",
        "erp_version": "ERP Version",
        "database": "Database",
        "module_complexity": "Module Complexity",
    }
    
    labels_map = _(labels_map_ko, labels_map_en)
    categories = [labels_map.get(k, k) for k in breakdown]
    values = list(breakdown.values())
    categories.append(categories[0])
    values.append(values[0])

    fig = go.Figure(go.Scatterpolar(
        r=values,
        theta=categories,
        fill="toself",
        fillcolor=f"rgba(0, 112, 242, 0.15)",
        line={"color": SAP_BLUE, "width": 2},
        marker={"size": 6, "color": SAP_BLUE},
    ))
    fig.update_layout(
        polar={"radialaxis": {"visible": True, "range": [0, 100]}},
        height=300,
        margin=dict(t=30, b=30, l=60, r=60),
        title={"text": _("항목별 점수 분석", "Score Breakdown Analysis"), "font": {"size": 14}},
    )
    return fig


def _render_tech_debt_chart(tech_debt: dict[str, float]) -> go.Figure:
    """모듈별 기술 부채 수평 바 차트."""
    sorted_items = sorted(tech_debt.items(), key=lambda x: x[1], reverse=True)
    modules = [item[0] for item in sorted_items]
    scores = [item[1] for item in sorted_items]

    colors = []
    for s in scores:
        if s >= 50:
            colors.append(SAP_RED)
        elif s >= 25:
            colors.append(SAP_ORANGE)
        else:
            colors.append(SAP_GREEN)

    fig = go.Figure(go.Bar(
        x=scores,
        y=modules,
        orientation="h",
        marker={"color": colors},
        text=[f"{s:.1f}" for s in scores],
        textposition="outside",
    ))
    fig.update_layout(
        title={"text": _("모듈별 기술 부채 (Technical Debt)", "Technical Debt by Module"), "font": {"size": 14}},
        xaxis_title=_("기술 부채 점수", "Technical Debt Score"),
        yaxis={"autorange": "reversed"},
        height=max(250, len(modules) * 45 + 100),
        margin=dict(t=50, b=40, l=50, r=30),
    )
    return fig


def _render_tco_chart(
    current_tco: float,
    projected_tco: float,
    savings_3yr: float,
) -> go.Figure:
    """TCO 비교 바 차트 (현재 vs 전환 후 + 3년 누적)."""
    years = ["Year 1", "Year 2", "Year 3"]
    current_costs = [current_tco] * 3
    projected_costs = [projected_tco] * 3
    cumulative_savings = [
        current_tco - projected_tco,
        (current_tco - projected_tco) * 2,
        savings_3yr,
    ]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        name=_("현재 TCO (As-Is)", "Current TCO (As-Is)"),
        x=years,
        y=current_costs,
        marker_color=SAP_RED,
        opacity=0.8,
        text=[_("{}억", "{}B").format(f"{v:.1f}") for v in current_costs],
        textposition="auto",
    ))

    fig.add_trace(go.Bar(
        name=_("전환 후 TCO (To-Be)", "Projected TCO (To-Be)"),
        x=years,
        y=projected_costs,
        marker_color=SAP_BLUE,
        opacity=0.8,
        text=[_("{}억", "{}B").format(f"{v:.1f}") for v in projected_costs],
        textposition="auto",
    ))

    fig.add_trace(go.Scatter(
        name=_("누적 절감액", "Cumulative Savings"),
        x=years,
        y=cumulative_savings,
        mode="lines+markers+text",
        line={"color": SAP_GREEN, "width": 3, "dash": "dot"},
        marker={"size": 10},
        text=[_("{}억", "{}B").format(f"{v:+.1f}") for v in cumulative_savings],
        textposition="top center",
        yaxis="y2",
    ))

    fig.update_layout(
        title={"text": _("TCO 비교 분석 (연간)", "TCO Comparison Analysis (Annual)"), "font": {"size": 14}},
        yaxis={"title": _("연간 비용 (억원)", "Annual Cost (100M KRW)")},
        yaxis2={
            "title": _("누적 절감액 (억원)", "Cumulative Savings (100M KRW)"),
            "overlaying": "y",
            "side": "right",
            "showgrid": False,
        },
        barmode="group",
        height=380,
        margin=dict(t=50, b=40, l=50, r=50),
        legend={"orientation": "h", "y": -0.15},
    )
    return fig


def render_dashboard(
    output: AdvisorOutput,
    customer_input: CustomerInput,
    pdf_bytes: bytes | None = None,
) -> None:
    """Advisor 결과를 대시보드 형태로 렌더링."""

    st.markdown("---")
    st.markdown(
        f"<h2 style='text-align:center;'>📊 {customer_input.company_name} – "
        + _("Clean Core Assessment 결과", "Clean Core Assessment Results") + "</h2>",
        unsafe_allow_html=True,
    )

    if output.generation_mode == "llm":
        st.success(_("🤖 AI 생성 리포트", "🤖 AI Generated Report"))
    else:
        st.info(
            _(
                "🧩 규칙 기반 리포트(자동 전환) - 일부 AI 단계 이슈가 있어 안정 모드 결과를 제공합니다.",
                "🧩 Rule-based report (auto fallback) - Stability mode was used due to issues in an AI stage.",
            )
        )

    # ── 핵심 KPI 카드 ──
    # ── 핵심 KPI 카드 ──
    # 프리미엄 KPI 위젯 스타일
    st.markdown("""
    <style>
    div[data-testid="metric-container"] {
        background-color: white;
        border: 1px solid #E9ECEF;
        padding: 5% 5% 5% 10%;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.04);
        border-left: 5px solid #0070F2;
    }
    div[data-testid="metric-container"] label {
        color: #6C757D !important;
        font-weight: 600;
        font-size: 0.9rem;
    }
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
        font-size: 1.8rem;
        font-weight: 800;
        color: #1B2559;
    }
    </style>
    """, unsafe_allow_html=True)
    
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.metric("Clean Core Score 🏆", f"{output.clean_core_score:.1f} / 100")
    with kpi2:
        st.metric(
            _("현재 연간 TCO 📉", "Current Annual TCO 📉"),
            _("{}억원", "{}B").format(_format_b_krw(output.current_annual_tco)),
        )
    with kpi3:
        delta_tco = output.projected_tco_after_migration - output.current_annual_tco
        st.metric(
            _("전환 후 TCO 예상 📊", "Projected TCO 📊"),
            _("{}억원", "{}B").format(_format_b_krw(output.projected_tco_after_migration)),
            delta=_("{}억원", "{}B").format(f"{delta_tco:+.2f}" if abs(delta_tco) < 10 else f"{delta_tco:+.1f}"),
            delta_color="inverse",
        )
    with kpi4:
        st.metric(
            _("3년 누적 TCO 절감 💰", "3-Year TCO Savings 💰"),
            _("{}억원", "{}B").format(_format_b_krw(output.tco_savings_3yr)),
        )

    # ── 리스크 수준 배지 ──
    risk_color = RISK_COLORS.get(output.risk_level, SAP_ORANGE)
    st.markdown(
        f"<div style='text-align:center; margin: 8px 0 16px;'>"
        f"<span style='background:{risk_color}; color:white; padding:6px 20px; "
        f"border-radius:20px; font-weight:bold;'>"
        + _("리스크 수준: ", "Risk Level: ") + f"{output.risk_level}</span></div>",
        unsafe_allow_html=True,
    )

    # ── 차트 Row 1: 게이지 + 레이더 ──
    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        st.plotly_chart(
            _render_score_gauge(output.clean_core_score),
            use_container_width=True,
        )
    with chart_col2:
        st.plotly_chart(
            _render_score_breakdown(output.score_breakdown),
            use_container_width=True,
        )

    # ── 차트 Row 2: 기술 부채 + TCO ──
    chart_col3, chart_col4 = st.columns(2)
    with chart_col3:
        st.plotly_chart(
            _render_tech_debt_chart(output.tech_debt_breakdown),
            use_container_width=True,
        )
    with chart_col4:
        st.plotly_chart(
            _render_tco_chart(
                output.current_annual_tco,
                output.projected_tco_after_migration,
                output.tco_savings_3yr,
            ),
            use_container_width=True,
        )

    # ── 리스크 요인 ──
    if output.risk_factors:
        st.subheader(_("⚠️ 주요 리스크 요인", "⚠️ Key Risk Factors"))
        for rf in output.risk_factors:
            st.markdown(f"- 🔸 {rf}")

    if output.validation_warnings:
        st.subheader(_("🧪 입력 검증 경고", "🧪 Input Validation Warnings"))
        for warning in output.validation_warnings:
            st.markdown(f"- ⚠️ {warning}")

    # ── 핵심 권고사항 ──
    if output.recommendations:
        st.subheader(_("💡 핵심 권고사항", "💡 Core Recommendations"))
        for idx, rec in enumerate(output.recommendations, 1):
            st.markdown(f"**{idx}.** {rec}")

    if output.evidence_ledger:
        st.subheader(_("🔗 근거 체인 (Evidence Ledger)", "🔗 Evidence Ledger"))
        table_rows = []
        for item in output.evidence_ledger:
            table_rows.append(
                {
                    "Claim": item.claim_text,
                    "Grade": item.evidence_grade,
                    "Rules": ", ".join(item.rule_ids) if item.rule_ids else "-",
                    "Sources": ", ".join(item.rag_sources) if item.rag_sources else "-",
                    "Ref IDs": ", ".join(item.reference_source_ids) if item.reference_source_ids else "-",
                }
            )
        st.dataframe(table_rows, use_container_width=True, hide_index=True)

    st.markdown("---")

    # ── Executive Summary ──
    st.subheader(_("📝 Executive Summary", "📝 Executive Summary"))
    st.markdown(output.executive_summary)

    # ── 상세 리포트 (접을 수 있는 expander) ──
    with st.expander(_("📖 상세 분석 리포트 (클릭하여 펼치기)", "📖 Detailed Analysis Report (Click to Expand)"), expanded=False):
        st.markdown(output.detailed_report)

    # ── PDF 다운로드 ──
    if pdf_bytes:
        st.markdown("---")
        st.subheader(_("📥 EA Cookbook 다운로드", "📥 Download EA Cookbook"))
        st.caption(
            _("분석 결과를 'Preliminary EA Cookbook' PDF로 다운로드하세요. 고객 미팅 전 초안 자료로 활용할 수 있습니다.",
              "Download the analysis results as a 'Preliminary EA Cookbook' PDF. Use it as a draft for client meetings.")
        )
        safe_name = customer_input.company_name.replace(" ", "_")
        st.download_button(
            label=_("📄 PDF 다운로드 – EA Cookbook", "📄 Download PDF – EA Cookbook"),
            data=pdf_bytes,
            file_name=f"EA_Cookbook_{safe_name}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
