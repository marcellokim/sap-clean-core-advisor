"""결과 대시보드 (Streamlit + Plotly).

Clean Core Score 게이지, 기술 부채 히트맵, TCO 비교 차트,
리스크 요인, Executive Summary, PDF 다운로드를 포함합니다.
"""

from __future__ import annotations

from html import escape

import plotly.graph_objects as go
import streamlit as st

from models.schemas import AdvisorOutput, CustomerInput
from ui.locales import _
from ui.styles import PRIMARY_FONT_STACK, render_section_heading, status_badge_markup

# ────────────────────────────────────────────────────────────────────
# 색상 팔레트 (SAP 톤)
# ────────────────────────────────────────────────────────────────────
SAP_BLUE = "#0070F2"
SAP_DARK = "#1B2559"
SAP_GREEN = "#36A41D"
SAP_ORANGE = "#E76500"
SAP_RED = "#BB0000"
SAP_LINE = "#D9E2EC"
SAP_BG = "rgba(0,0,0,0)"

RISK_COLORS = {"High": SAP_RED, "Medium": SAP_ORANGE, "Low": SAP_GREEN}
RISK_TONES = {"High": "high", "Medium": "medium", "Low": "low"}


def _format_b_krw(value: float) -> str:
    """Format billion-KRW values with enough precision to surface small differences."""
    return f"{value:.2f}" if abs(value) < 10 else f"{value:.1f}"


def _apply_chart_theme(fig: go.Figure) -> go.Figure:
    """Apply the shared dashboard chart theme without changing chart semantics."""
    fig.update_layout(
        paper_bgcolor=SAP_BG,
        plot_bgcolor=SAP_BG,
        font={"family": PRIMARY_FONT_STACK, "color": SAP_DARK},
        title_font={"color": SAP_DARK},
        legend_font={"color": SAP_DARK},
    )
    return fig


def _render_markdown_list(items: list[str], *, ordered: bool = False) -> str:
    """Return consistent HTML list markup for surface panels."""
    if not items:
        return ""

    tag = "ol" if ordered else "ul"
    item_markup = "".join(f"<li>{escape(item)}</li>" for item in items)
    return f"<{tag} class='advisor-list-tight'>{item_markup}</{tag}>"


def _report_mode_copy(output: AdvisorOutput) -> tuple[str, str, str]:
    """Return localized messaging for the current narrative generation mode."""
    if output.generation_mode == "llm":
        return (
            _("Narrative mode", "Narrative mode"),
            _("AI 생성", "AI generated"),
            _(
                "AI와 규칙 기반 분석을 함께 사용해 임원용 내러티브를 생성했습니다.",
                "The executive narrative was produced with AI assistance on top of the rules-based analysis.",
            ),
        )

    return (
        _("Narrative mode", "Narrative mode"),
        _("안정 모드", "Stability mode"),
        _(
            "일부 AI 단계 이슈로 규칙 기반 안정 모드 결과를 제공했습니다.",
            "A rules-based stability-mode narrative was provided because an AI step was unavailable.",
        ),
    )


def _render_score_gauge(score: float) -> go.Figure:
    """Clean Core Score 게이지 차트."""
    if score >= 70:
        bar_color = SAP_GREEN
    elif score >= 40:
        bar_color = SAP_ORANGE
    else:
        bar_color = SAP_RED

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            number={"suffix": " / 100", "font": {"size": 28}},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": SAP_DARK},
                "bar": {"color": bar_color, "thickness": 0.75},
                "bgcolor": "rgba(255,255,255,0)",
                "borderwidth": 0,
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
        )
    )
    fig.update_layout(height=280, margin=dict(t=60, b=20, l=30, r=30))
    return _apply_chart_theme(fig)


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

    fig = go.Figure(
        go.Scatterpolar(
            r=values,
            theta=categories,
            fill="toself",
            fillcolor="rgba(0, 112, 242, 0.15)",
            line={"color": SAP_BLUE, "width": 2},
            marker={"size": 6, "color": SAP_BLUE},
        )
    )
    fig.update_layout(
        polar={
            "radialaxis": {
                "visible": True,
                "range": [0, 100],
                "gridcolor": SAP_LINE,
                "linecolor": SAP_LINE,
            }
        },
        height=300,
        margin=dict(t=30, b=30, l=60, r=60),
        title={"text": _("항목별 점수 분석", "Score Breakdown Analysis"), "font": {"size": 14}},
    )
    return _apply_chart_theme(fig)


def _render_tech_debt_chart(tech_debt: dict[str, float]) -> go.Figure:
    """모듈별 기술 부채 수평 바 차트."""
    sorted_items = sorted(tech_debt.items(), key=lambda x: x[1], reverse=True)
    modules = [item[0] for item in sorted_items]
    scores = [item[1] for item in sorted_items]

    colors = []
    for score in scores:
        if score >= 50:
            colors.append(SAP_RED)
        elif score >= 25:
            colors.append(SAP_ORANGE)
        else:
            colors.append(SAP_GREEN)

    fig = go.Figure(
        go.Bar(
            x=scores,
            y=modules,
            orientation="h",
            marker={"color": colors},
            text=[f"{score:.1f}" for score in scores],
            textposition="outside",
        )
    )
    fig.update_layout(
        title={"text": _("모듈별 기술 부채", "Technical debt by module"), "font": {"size": 14}},
        xaxis={"title": _("기술 부채 점수", "Technical debt score"), "gridcolor": SAP_LINE},
        yaxis={"autorange": "reversed", "gridcolor": SAP_BG},
        height=max(250, len(modules) * 45 + 100),
        margin=dict(t=50, b=40, l=50, r=30),
    )
    return _apply_chart_theme(fig)


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
    fig.add_trace(
        go.Bar(
            name=_("현재 TCO (As-Is)", "Current TCO (As-Is)"),
            x=years,
            y=current_costs,
            marker_color=SAP_RED,
            opacity=0.85,
            text=[_("{}억", "{}B").format(f"{value:.1f}") for value in current_costs],
            textposition="auto",
        )
    )
    fig.add_trace(
        go.Bar(
            name=_("전환 후 TCO (To-Be)", "Projected TCO (To-Be)"),
            x=years,
            y=projected_costs,
            marker_color=SAP_BLUE,
            opacity=0.85,
            text=[_("{}억", "{}B").format(f"{value:.1f}") for value in projected_costs],
            textposition="auto",
        )
    )
    fig.add_trace(
        go.Scatter(
            name=_("누적 절감액", "Cumulative Savings"),
            x=years,
            y=cumulative_savings,
            mode="lines+markers+text",
            line={"color": SAP_GREEN, "width": 3, "dash": "dot"},
            marker={"size": 10},
            text=[_("{}억", "{}B").format(f"{value:+.1f}") for value in cumulative_savings],
            textposition="top center",
            yaxis="y2",
        )
    )
    fig.update_layout(
        title={"text": _("TCO 비교 분석", "TCO comparison analysis"), "font": {"size": 14}},
        yaxis={"title": _("연간 비용 (억원)", "Annual cost (100M KRW)"), "gridcolor": SAP_LINE},
        yaxis2={
            "title": _("누적 절감액 (억원)", "Cumulative savings (100M KRW)"),
            "overlaying": "y",
            "side": "right",
            "showgrid": False,
        },
        barmode="group",
        height=380,
        margin=dict(t=50, b=40, l=50, r=50),
        legend={"orientation": "h", "y": -0.15},
    )
    return _apply_chart_theme(fig)


def render_dashboard(
    output: AdvisorOutput,
    customer_input: CustomerInput,
    pdf_bytes: bytes | None = None,
) -> None:
    """Advisor 결과를 대시보드 형태로 렌더링."""
    mode_label, mode_value, mode_note = _report_mode_copy(output)
    badge_markup = (
        "<div class='advisor-badge-row'>"
        + status_badge_markup(
            label=_("리스크", "Risk"),
            value=output.risk_level,
            tone=RISK_TONES.get(output.risk_level, "neutral"),
        )
        + status_badge_markup(label=mode_label, value=mode_value)
        + "</div>"
    )

    with st.container(border=True):
        render_section_heading(
            eyebrow="Assessment results",
            title=f"{customer_input.company_name} — Clean Core Assessment",
            description=_(
                "경영진 요약, 재무 영향, 기술 부채 시그널을 한 화면에서 검토할 수 있도록 재구성했습니다.",
                "The results are reorganized so you can review executive narrative, financial impact, and technical debt signals in one place.",
            ),
        )
        st.markdown(badge_markup, unsafe_allow_html=True)
        st.markdown(
            "<div class='advisor-note-card'>"
            f"<span class='advisor-note-card__label'>{escape(_("Narrative summary", "Narrative summary"))}</span>"
            f"<p class='advisor-note-card__body'>{escape(mode_note)}</p>"
            "</div>",
            unsafe_allow_html=True,
        )

    with st.container(border=True):
        render_section_heading(
            eyebrow="Executive snapshot",
            title=_("핵심 KPI", "Core KPIs"),
            description=_(
                "점수, 현재 비용, 전환 후 비용, 3년 누적 절감액을 먼저 확인하세요.",
                "Review the score, current cost, target cost, and three-year savings first.",
            ),
        )
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        with kpi1:
            st.metric("Clean Core Score", f"{output.clean_core_score:.1f} / 100")
        with kpi2:
            st.metric(
                _("현재 연간 TCO", "Current Annual TCO"),
                _("{}억원", "{}B").format(_format_b_krw(output.current_annual_tco)),
            )
        with kpi3:
            delta_tco = output.projected_tco_after_migration - output.current_annual_tco
            st.metric(
                _("전환 후 연간 TCO", "Projected Annual TCO"),
                _("{}억원", "{}B").format(_format_b_krw(output.projected_tco_after_migration)),
                delta=_("{}억원", "{}B").format(
                    f"{delta_tco:+.2f}" if abs(delta_tco) < 10 else f"{delta_tco:+.1f}"
                ),
                delta_color="inverse",
            )
        with kpi4:
            st.metric(
                _("3년 누적 TCO 절감", "3-Year TCO Savings"),
                _("{}억원", "{}B").format(_format_b_krw(output.tco_savings_3yr)),
            )

    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        with st.container(border=True):
            render_section_heading(
                eyebrow="Score",
                title=_("클린 코어 점수", "Clean Core score"),
                description=_(
                    "현재 표준 준수 수준을 게이지로 확인합니다.",
                    "Review the current standards alignment through the score gauge.",
                ),
            )
            st.plotly_chart(_render_score_gauge(output.clean_core_score), use_container_width=True)
    with chart_col2:
        with st.container(border=True):
            render_section_heading(
                eyebrow="Drivers",
                title=_("점수 구성요소", "Score drivers"),
                description=_(
                    "커스텀 코드, ERP 버전, 데이터베이스, 모듈 복잡도를 함께 봅니다.",
                    "Compare custom code, ERP version, database, and module complexity together.",
                ),
            )
            st.plotly_chart(_render_score_breakdown(output.score_breakdown), use_container_width=True)

    chart_col3, chart_col4 = st.columns(2)
    with chart_col3:
        with st.container(border=True):
            render_section_heading(
                eyebrow="Technical debt",
                title=_("모듈별 기술 부채", "Technical debt by module"),
                description=_(
                    "부채가 높은 모듈부터 우선순위를 판단할 수 있습니다.",
                    "Use this view to prioritize the modules carrying the most debt.",
                ),
            )
            st.plotly_chart(_render_tech_debt_chart(output.tech_debt_breakdown), use_container_width=True)
    with chart_col4:
        with st.container(border=True):
            render_section_heading(
                eyebrow="Financial impact",
                title=_("TCO 비교", "TCO comparison"),
                description=_(
                    "현재와 전환 후 비용 구조, 누적 절감 효과를 함께 봅니다.",
                    "Review current versus target cost structure together with cumulative savings.",
                ),
            )
            st.plotly_chart(
                _render_tco_chart(
                    output.current_annual_tco,
                    output.projected_tco_after_migration,
                    output.tco_savings_3yr,
                ),
                use_container_width=True,
            )

    insight_col1, insight_col2 = st.columns(2)
    with insight_col1:
        with st.container(border=True):
            render_section_heading(
                eyebrow="Risk watchlist",
                title=_("운영 리스크 및 검증 경고", "Operational risks and validation warnings"),
                description=_(
                    "추가 확인이 필요한 리스크와 입력 경고를 한데 모았습니다.",
                    "Operational risks and input warnings that need follow-up are grouped together here.",
                ),
            )
            if output.risk_factors:
                st.markdown(_render_markdown_list(output.risk_factors), unsafe_allow_html=True)
            else:
                st.caption(_("현재 추가 리스크 요인은 없습니다.", "No additional risk factors were surfaced."))

            if output.validation_warnings:
                st.caption(_("입력 검증 경고", "Input validation warnings"))
                st.markdown(_render_markdown_list(output.validation_warnings), unsafe_allow_html=True)
    with insight_col2:
        with st.container(border=True):
            render_section_heading(
                eyebrow="Actions",
                title=_("핵심 권고사항", "Core recommendations"),
                description=_(
                    "다음 단계 의사결정에 필요한 실행 권고안을 우선순위로 정리했습니다.",
                    "The recommended next actions are organized for executive prioritization.",
                ),
            )
            if output.recommendations:
                st.markdown(_render_markdown_list(output.recommendations, ordered=True), unsafe_allow_html=True)
            else:
                st.caption(_("현재 추가 권고사항은 없습니다.", "No additional recommendations are available."))

    if output.evidence_ledger:
        with st.container(border=True):
            render_section_heading(
                eyebrow="Evidence ledger",
                title=_("근거 체인", "Evidence ledger"),
                description=_(
                    "주요 claim과 규칙, 소스 연결 상태를 확인할 수 있습니다.",
                    "Review the supporting claims, rules, and source-linking evidence here.",
                ),
            )
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

    summary_col, detail_col = st.columns([1.2, 1])
    with summary_col:
        with st.container(border=True):
            render_section_heading(
                eyebrow="Executive narrative",
                title=_("요약", "Executive summary"),
                description=_(
                    "의사결정자가 바로 읽을 수 있도록 핵심 메시지를 전면에 배치했습니다.",
                    "The top-line narrative is surfaced so decision-makers can review it immediately.",
                ),
            )
            st.markdown(output.executive_summary)
    with detail_col:
        with st.container(border=True):
            render_section_heading(
                eyebrow="Detailed view",
                title=_("상세 분석 리포트", "Detailed analysis report"),
                description=_(
                    "세부 리포트는 필요한 경우에만 펼쳐서 읽을 수 있습니다.",
                    "Expand the detailed report only when you need the supporting analysis.",
                ),
            )
            with st.expander(_("상세 분석 펼치기", "Open detailed analysis"), expanded=False):
                st.markdown(output.detailed_report)

    if pdf_bytes:
        with st.container(border=True):
            render_section_heading(
                eyebrow="Deliverable",
                title=_("EA Cookbook 다운로드", "EA Cookbook download"),
                description=_(
                    "분석 결과를 임원 미팅용 PDF 초안으로 내려받을 수 있습니다.",
                    "Download the assessment as a PDF draft for executive review or workshop prep.",
                ),
            )
            safe_name = customer_input.company_name.replace(" ", "_")
            st.download_button(
                label=_("EA Cookbook PDF 다운로드", "Download EA Cookbook PDF"),
                data=pdf_bytes,
                file_name=f"EA_Cookbook_{safe_name}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
