"""Clean Core tab rendering and handler wiring."""

from __future__ import annotations

import streamlit as st

from config.settings import settings
from models.schemas import CustomerInput
from services.analysis_service import analyze_customer_input
from ui.dashboard import render_dashboard
from ui.input_form import render_input_form
from ui.locales import _
from ui.policy import get_locked_analysis_policy


def _current_llm_provider() -> str:
    return settings.LLM_PROVIDER.strip().lower() or "gemini"


def _render_empty_state() -> None:
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


def _show_analysis_error(exc: Exception) -> None:
    err_msg = str(exc).strip()
    provider = _current_llm_provider()
    key_missing = False
    if provider in {"glm", "glm-5", "zhipu"}:
        key_missing = not settings.GLM_API_KEY.strip()
    else:
        key_missing = not settings.GOOGLE_API_KEY.strip()

    if key_missing:
        st.error(
            _(
                "분석 중 오류가 발생했습니다.\n\n선택한 LLM provider API 키가 .env 파이에 설정되어 있는지 확인하세요.",
                "An error occurred during analysis.\n\nPlease check if LLM provider API key is set in .env file.",
            )
        )
        return

    st.error(
        _(
            "분석 중 오류가 발생했습니다. 네트워크 상태 또는 API 한도를 확인하세요.",
            "An error occurred during analysis. Check network or API limits.",
        )
    )
    if err_msg:
        st.caption(_(f"상세 오류: {err_msg}", f"Error Details: {err_msg}"))


def _store_analysis_state(
    customer_input: CustomerInput,
    output: object,
    pdf_bytes: bytes | None,
) -> None:
    st.session_state["last_output"] = output
    st.session_state["last_input"] = customer_input
    st.session_state["last_pdf"] = pdf_bytes


def render_clean_core_tab() -> None:
    """Render the Clean Core analysis tab."""

    customer_input: CustomerInput | None = render_input_form()
    if customer_input is None:
        _render_empty_state()
        return

    status_msg = _(
        "🔄 AI가 SAP Clean Core 분석을 수행하고 있습니다... (캐시된 결과가 없다면 약 30-60초 소요)",
        "🔄 AI is performing Clean Core Analysis... (Approx 30-60s if not cached)",
    )
    with st.status(status_msg, expanded=True) as status:
        try:
            st.write(_("고객 데이터 룰셋 매핑 중...", "Mapping customer data to rulesets..."))
            policy = get_locked_analysis_policy()
            lang = st.session_state.get("ui_lang", "KO").lower()
            st.write(
                _(
                    "비용 계산 및 AI 로드맵 생성 (RAG/LLM)...",
                    "Running TCO calculation and AI generation (RAG/LLM)...",
                )
            )
            analysis_result = analyze_customer_input(customer_input, lang=lang, policy=policy)
        except Exception as exc:
            _show_analysis_error(exc)
            status.update(label=_("분석 실패", "Analysis Failed"), state="error", expanded=True)
            return

        status.update(label=_("✅ 분석 완료!", "✅ Analysis Complete!"), state="complete", expanded=False)

    if analysis_result.pdf_error_code:
        st.warning(
            _(
                "PDF 생성에 실패하여 화면 결과만 제공합니다. (코드: {})",
                "Failed to generate PDF, providing UI results only. (Code: {})",
            ).format(analysis_result.pdf_error_code)
        )
        if analysis_result.pdf_error_message:
            st.caption(
                _("PDF 오류 상세: {}", "PDF Error Details: {}").format(
                    analysis_result.pdf_error_message
                )
            )

    _store_analysis_state(customer_input, analysis_result.output, analysis_result.pdf_bytes)
    render_dashboard(analysis_result.output, customer_input, analysis_result.pdf_bytes)
