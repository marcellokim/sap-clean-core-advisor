"""SAP Clean Core Advisor – 메인 Streamlit 앱.

입력 → 규칙 기반 계산 → AI 분석(RAG) → 시각화 → PDF 다운로드 전체 플로우를 통합합니다.
"""

from pathlib import Path

import streamlit as st

from models.schemas import CustomerInput
from services.infrastructure.rag.chroma_provider import get_cached_vector_store
from ui.dashboard import render_dashboard
from ui.input_form import render_input_form
from ui.policy import get_locked_analysis_policy
from ui.sidebar import render_sidebar
from ui.styles import apply_global_styles
from config.settings import settings
from ui.locales import _

DOCS_ROOT = Path(__file__).resolve().parent / "docs"
LOGO_PATH = Path(__file__).resolve().parent / "data" / "assets" / "sap_logo.svg"


def _current_llm_provider() -> str:
    return settings.LLM_PROVIDER.strip().lower() or "gemini"

# ────────────────────────────────────────────────────────────────────
# 페이지 설정
# ────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="RISE with SAP: Clean Core Assessment",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 고급 UI/UX를 위한 글로벌 CSS 주입
apply_global_styles()

# ────────────────────────────────────────────────────────────────────
# 사이드바
# ────────────────────────────────────────────────────────────────────
render_sidebar(LOGO_PATH, DOCS_ROOT)


# ────────────────────────────────────────────────────────────────────
# 메인 영역
# ────────────────────────────────────────────────────────────────────
def main() -> None:
    """메인 앱 플로우."""
    if settings.RAG_WARMUP_ON_START:
        try:
            get_cached_vector_store()
        except Exception:
            pass

    # 기본 메인 상단 타이틀
    st.markdown(
        "<h1 style='text-align:center;'>🏗️ RISE with SAP: Clean Core Assessment</h1>"
        "<p style='text-align:center; color:gray;'>"
        + _("AI 기반 SAP 레거시 시스템 진단 및 전환 전략 도우미", "AI-driven SAP Legacy System Assessment & Strategy Assistant") +
        "</p>",
        unsafe_allow_html=True,
    )

    tab_cc, tab_joule = st.tabs([
        _("🔍 Clean Core Assessment", "🔍 Clean Core Assessment"),
        _("🤖 Joule Readiness Checklist", "🤖 Joule Readiness Checklist")
    ])

    with tab_cc:
        _render_clean_core_tab()

    with tab_joule:
        from ui.joule_checklist import render_joule_checklist
        from services.domain.joule_readiness_engine import generate_joule_gap_analysis

        def _handle_gap_analysis(checked: list[str], unchecked: list[str]):
            status_msg = _("🧠 AI가 Gap Analysis 리포트를 작성 중입니다...", "🧠 AI is compiling the Gap Analysis Report...")
            with st.status(status_msg, expanded=True) as status:
                st.write(_("고객 데이터 룰셋 매핑 중...", "Mapping customer data to rulesets..."))
                result = generate_joule_gap_analysis(checked, unchecked)
                status.update(label=_("✅ 분석 완료!", "✅ Analysis Complete!"), state="complete", expanded=False)
                
                st.markdown("---")
                st.subheader(_("📊 Joule Readiness Gap Analysis 리포트", "📊 Joule Readiness Gap Analysis Report"))
                
                # 리스크 뱃지
                risk_colors = {"High": "#BB0000", "Medium": "#E76500", "Low": "#36A41D"}
                color = risk_colors.get(result.risk_level, "#36A41D")
                st.markdown(
                    f"<div style='margin-bottom: 12px;'>"
                    f"<span style='background:{color}; color:white; padding:4px 12px; "
                    f"border-radius:12px; font-weight:bold;'>"
                    + _("리스크 수준: ", "Risk Level: ") + f"{result.risk_level}</span></div>",
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
                        
        render_joule_checklist(_handle_gap_analysis)


def _render_clean_core_tab() -> None:
    """메인 Clean Core 분석 탭"""

    customer_input: CustomerInput | None = render_input_form()

    if customer_input is None:
        st.markdown("---")
        info_ko = (
            "👆 위 폼에 고객사 정보를 입력하고 **'Clean Core 분석 시작'** 버튼을 눌러주세요.\n\n"
            "분석 결과로 다음을 제공합니다:\n"
            "- **Clean Core Score** (0-100) – 현재 시스템의 표준 준수도\n"
            "- **기술 부채 히트맵** – 모듈별 커스텀 부채 시각화\n"
            "- **TCO 비교 분석** – 현재 vs 전환 후 비용 비교\n"
            "- **AI 기반 진단 리포트** – 리스크 평가 및 전환 전략\n"
            "- **EA Cookbook PDF** – 임원 보고용 문서 자동 생성"
        )
        info_en = (
            "👆 Enter your company details above and click **'Start Clean Core Analysis'**.\n\n"
            "The analysis will provide:\n"
            "- **Clean Core Score** (0-100) – Standard compliance of current system\n"
            "- **Tech Debt Heatmap** – Visualized custom debt by module\n"
            "- **TCO Comparative Analysis** – Current vs Projected costs\n"
            "- **AI Diagnosis Report** – Risk assessment & transition strategy\n"
            "- **EA Cookbook PDF** – Automatically generated executive report"
        )
        st.info(_(info_ko, info_en))
        return

    status_msg = _(
        "🔄 AI가 SAP Clean Core 분석을 수행하고 있습니다... (캐시된 결과가 없다면 약 30-60초 소요)",
        "🔄 AI is performing Clean Core Analysis... (Approx 30-60s if not cached)"
    )
    with st.status(status_msg, expanded=True) as status:
        try:
            st.write(_("고객 데이터 룰셋 매핑 중...", "Mapping customer data to rulesets..."))
            policy = get_locked_analysis_policy()
            lang = st.session_state.get("ui_lang", "KO").lower()
            
            st.write(_("비용 계산 및 AI 로드맵 생성 (RAG/LLM)...", "Running TCO calculation and AI generation (RAG/LLM)..."))
            # Use the newly added cached wrapper avoiding serialization issues
            from services.analysis_service import analyze_customer_input
            analysis_result = analyze_customer_input(customer_input, lang=lang, policy=policy)
            output = analysis_result.output
            pdf_bytes = analysis_result.pdf_bytes
        except Exception as e:
            err_msg = str(e).strip()
            provider = _current_llm_provider()
            key_missing = False
            if provider in {"glm", "glm-5", "zhipu"}:
                key_missing = not settings.GLM_API_KEY.strip()
            else:
                key_missing = not settings.GOOGLE_API_KEY.strip()

            if key_missing:
                st.error(
                    _("분석 중 오류가 발생했습니다.\n\n선택한 LLM provider API 키가 .env 파이에 설정되어 있는지 확인하세요.",
                      "An error occurred during analysis.\n\nPlease check if LLM provider API key is set in .env file.")
                )
            else:
                st.error(_("분석 중 오류가 발생했습니다. 네트워크 상태 또는 API 한도를 확인하세요.", "An error occurred during analysis. Check network or API limits."))
                if err_msg:
                    st.caption(_(f"상세 오류: {err_msg}", f"Error Details: {err_msg}"))
            status.update(label=_("분석 실패", "Analysis Failed"), state="error", expanded=True)
            return

        status.update(label=_("✅ 분석 완료!", "✅ Analysis Complete!"), state="complete", expanded=False)

    if analysis_result.pdf_error_code:
        st.warning(
            _("PDF 생성에 실패하여 화면 결과만 제공합니다. (코드: {})", "Failed to generate PDF, providing UI results only. (Code: {})").format(analysis_result.pdf_error_code)
        )
        if analysis_result.pdf_error_message:
            st.caption(_("PDF 오류 상세: {}", "PDF Error Details: {}").format(analysis_result.pdf_error_message))

    st.session_state["last_output"] = output
    st.session_state["last_input"] = customer_input
    st.session_state["last_pdf"] = pdf_bytes

    render_dashboard(output, customer_input, pdf_bytes)


if __name__ == "__main__":
    main()
