"""SAP Clean Core Advisor – 메인 Streamlit 앱.

입력 → 규칙 기반 계산 → AI 분석(RAG) → 시각화 → PDF 다운로드 전체 플로우를 통합합니다.
"""

from pathlib import Path

import streamlit as st

from config.settings import settings
from ui.sidebar import render_sidebar
from ui.locales import _
from ui.styles import apply_global_styles, render_shell_header

DOCS_ROOT = Path(__file__).resolve().parent / "docs"
LOGO_PATH = Path(__file__).resolve().parent / "data" / "assets" / "sap_logo.svg"
PAGE_ICON = str(LOGO_PATH) if LOGO_PATH.exists() else None

# ────────────────────────────────────────────────────────────────────
# 페이지 설정
# ────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SAP Clean Core Advisor",
    page_icon=PAGE_ICON,
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


def _tab_labels() -> list[str]:
    """Return the non-emoji tab labels for the shell."""
    return ["Clean Core Assessment", "Joule Readiness"]


def _render_tabs() -> None:
    """Import tab renderers at use time to keep default imports lightweight."""
    from ui.tabs import render_clean_core_tab, render_joule_tab

    tab_cc, tab_joule = st.tabs(_tab_labels())

    with tab_cc:
        render_clean_core_tab()

    with tab_joule:
        render_joule_tab()


def main() -> None:
    """메인 앱 플로우."""
    _maybe_warm_rag_vector_store()

    render_shell_header(
        eyebrow="RISE with SAP workspace",
        title="SAP Clean Core Advisor",
        description=_(
            "클린 코어 진단, TCO 시뮬레이션, Joule readiness 점검을 하나의 워크스페이스에서 정리하세요.",
            "Prepare Clean Core diagnostics, TCO simulation, and Joule readiness in one workspace.",
        ),
        highlights=[
            _("임원 보고용 인사이트", "Executive-ready insights"),
            _("규칙 기반 + AI 분석", "Rules plus AI analysis"),
            _("PDF 산출물 즉시 다운로드", "Instant PDF output"),
        ],
    )

    _render_tabs()


if __name__ == "__main__":
    main()
