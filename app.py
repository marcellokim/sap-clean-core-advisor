"""SAP Clean Core Advisor – 메인 Streamlit 앱.

입력 → 규칙 기반 계산 → AI 분석(RAG) → 시각화 → PDF 다운로드 전체 플로우를 통합합니다.
"""

from pathlib import Path

import streamlit as st

from config.settings import settings
from ui.sidebar import render_sidebar
from ui.locales import _
from ui.styles import apply_global_styles

DOCS_ROOT = Path(__file__).resolve().parent / "docs"
LOGO_PATH = Path(__file__).resolve().parent / "data" / "assets" / "sap_logo.svg"
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
def _maybe_warm_rag_vector_store() -> None:
    """Warm the vector store only when startup warmup is explicitly enabled."""
    if not settings.RAG_WARMUP_ON_START:
        return

    try:
        from services.infrastructure.rag.chroma_provider import get_cached_vector_store

        get_cached_vector_store()
    except Exception:
        pass


def _render_tabs() -> None:
    """Import tab renderers at use time to keep default imports lightweight."""
    from ui.tabs import render_clean_core_tab, render_joule_tab

    tab_cc, tab_joule = st.tabs([
        _("🔍 Clean Core Assessment", "🔍 Clean Core Assessment"),
        _("🤖 Joule Readiness Checklist", "🤖 Joule Readiness Checklist")
    ])

    with tab_cc:
        render_clean_core_tab()

    with tab_joule:
        render_joule_tab()


def main() -> None:
    """메인 앱 플로우."""
    _maybe_warm_rag_vector_store()

    # 기본 메인 상단 타이틀
    st.markdown(
        "<h1 style='text-align:center;'>🏗️ RISE with SAP: Clean Core Assessment</h1>"
        "<p style='text-align:center; color:gray;'>"
        + _("AI 기반 SAP 레거시 시스템 진단 및 전환 전략 도우미", "AI-driven SAP Legacy System Assessment & Strategy Assistant") +
        "</p>",
        unsafe_allow_html=True,
    )

    _render_tabs()


if __name__ == "__main__":
    main()
