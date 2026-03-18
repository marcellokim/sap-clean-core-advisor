"""Clean Core tab rendering and handler wiring."""

from __future__ import annotations

import streamlit as st

from config.settings import settings
from models.schemas import CustomerInput
from ui.input_form import render_input_form
from ui.locales import _
from ui.policy import get_locked_analysis_policy
from ui.styles import render_empty_state_panel


def analyze_customer_input(*args, **kwargs):
    """Lazy compatibility import for the analysis entrypoint."""
    from services.analysis_service import analyze_customer_input as impl

    return impl(*args, **kwargs)


def render_dashboard(*args, **kwargs):
    """Lazy dashboard import to keep the default app import path slim."""
    from ui.dashboard import render_dashboard as impl

    return impl(*args, **kwargs)


def _current_llm_provider() -> str:
    return settings.LLM_PROVIDER.strip().lower() or "gemini"


def _empty_state_content() -> tuple[str, str, list[str]]:
    """Return localized empty-state copy for the Clean Core tab."""
    return (
        _("분석 준비", "Prepare the assessment"),
        _(
            "상단 폼에 고객사 정보를 입력하면 Clean Core score, 기술 부채, TCO 비교, EA Cookbook 초안을 한 번에 생성합니다.",
            "Complete the intake form above to generate the Clean Core score, technical debt view, TCO comparison, and a draft EA Cookbook in one pass.",
        ),
        [
            _("Clean Core score와 표준 준수 수준", "Clean Core score and standards alignment"),
            _("모듈별 기술 부채 시각화", "Module-level technical debt visualization"),
            _("현재 대비 전환 후 TCO 비교", "Current versus target TCO comparison"),
            _("리스크와 전환 권고안이 담긴 executive summary", "Executive summary with risks and recommended actions"),
        ],
    )


def _render_empty_state() -> None:
    title, description, highlights = _empty_state_content()
    render_empty_state_panel(
        title=title,
        description=description,
        highlights=highlights,
    )


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
                "분석 중 오류가 발생했습니다. 선택한 LLM provider API 키가 .env 파일에 설정되어 있는지 확인하세요.",
                "An error occurred during analysis. Check that the selected LLM provider API key is configured in the .env file.",
            )
        )
        return

    st.error(
        _(
            "분석 중 오류가 발생했습니다. 네트워크 상태 또는 API 한도를 확인하세요.",
            "An error occurred during analysis. Check network status or API limits.",
        )
    )
    if err_msg:
        st.caption(_(f"상세 오류: {err_msg}", f"Error details: {err_msg}"))


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
        "AI가 SAP Clean Core 분석을 수행하고 있습니다. 캐시된 결과가 없다면 약 30~60초가 소요됩니다.",
        "AI is running the SAP Clean Core analysis. Expect roughly 30 to 60 seconds when no cached result is available.",
    )
    with st.status(status_msg, expanded=True) as status:
        try:
            st.write(_("고객 데이터 룰셋을 매핑하고 있습니다...", "Mapping customer data to rulesets..."))
            policy = get_locked_analysis_policy()
            lang = st.session_state.get("ui_lang", "KO").lower()
            st.write(
                _(
                    "비용 계산과 AI 기반 로드맵 생성을 수행하고 있습니다...",
                    "Running the cost model and AI-backed roadmap generation...",
                )
            )
            analysis_result = analyze_customer_input(customer_input, lang=lang, policy=policy)
        except Exception as exc:
            _show_analysis_error(exc)
            status.update(label=_("분석 실패", "Analysis failed"), state="error", expanded=True)
            return

        status.update(label=_("분석 완료", "Analysis complete"), state="complete", expanded=False)

    if analysis_result.pdf_error_code:
        st.warning(
            _(
                "PDF 생성에 실패하여 화면 결과만 제공합니다. (코드: {})",
                "PDF generation failed, so only the on-screen results are available. (Code: {})",
            ).format(analysis_result.pdf_error_code)
        )
        if analysis_result.pdf_error_message:
            st.caption(
                _("PDF 오류 상세: {}", "PDF error details: {}").format(
                    analysis_result.pdf_error_message
                )
            )

    _store_analysis_state(customer_input, analysis_result.output, analysis_result.pdf_bytes)
    render_dashboard(analysis_result.output, customer_input, analysis_result.pdf_bytes)
