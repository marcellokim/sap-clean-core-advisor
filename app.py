"""SAP Clean Core Advisor – 메인 Streamlit 앱.

입력 → 규칙 기반 계산 → AI 분석(RAG) → 시각화 → PDF 다운로드 전체 플로우를 통합합니다.
"""

import io
import zipfile
from pathlib import Path

import streamlit as st

from models.schemas import CustomerInput
from services.analysis_service import run_analysis
from services.infrastructure.rag.chroma_provider import get_cached_vector_store
from ui.dashboard import render_dashboard
from ui.input_form import render_input_form
from ui.policy import get_locked_analysis_policy
from config.settings import settings
from ui.locales import _

DOCS_ROOT = Path(__file__).resolve().parent / "docs"
LOGO_PATH = Path(__file__).resolve().parent / "data" / "assets" / "sap_logo.svg"


def _current_llm_provider() -> str:
    return settings.LLM_PROVIDER.strip().lower() or "gemini"


def _build_support_pack_zip(language_mode: str) -> bytes:
    """Build downloadable EA support pack ZIP bytes."""
    include_all = language_mode == "ALL"
    language_suffix = f"_{language_mode}.md"
    candidates: list[Path] = []
    for folder in ("workshop-kit", "joule-playbook", "ops-toolkit", "ea-cookbook"):
        folder_path = DOCS_ROOT / folder
        if not folder_path.exists():
            continue
        for path in sorted(folder_path.glob("*")):
            if path.is_dir():
                continue
            name = path.name
            if include_all:
                candidates.append(path)
            else:
                if name.endswith(language_suffix):
                    candidates.append(path)
                elif "_KO" not in name and "_EN" not in name:
                    candidates.append(path)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in candidates:
            arcname = str(path.relative_to(DOCS_ROOT.parent))
            zf.write(path, arcname=arcname)
    return buf.getvalue()

# ────────────────────────────────────────────────────────────────────
# 페이지 설정
# ────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="RISE with SAP: Clean Core Assessment",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ────────────────────────────────────────────────────────────────────
# 사이드바
# ────────────────────────────────────────────────────────────────────
with st.sidebar:
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=120)
    else:
        st.markdown("### SAP")
    
    st.markdown("## RISE with SAP")
    st.markdown("### Clean Core Assessment\n& TCO Simulator")
    st.divider()

    ui_lang = st.selectbox("UI Language / 언어", options=["KO", "EN"], index=0)
    st.session_state["ui_lang"] = ui_lang

    target_persona_ko = """
        **Target Persona**
        - 🏢 국내 중견 제조기업 CIO
        - 📦 15년+ 된 ECC 6.0 운영 중
        - 🔧 다수의 Z-code로 시스템 복잡도 ↑
        - 💰 클라우드 전환 검토 중

        **이 도구의 가치**
        - ⏱️ 초기 진단을 1분 만에 완료
        - 📊 Clean Core Score 자동 산출
        - 💹 TCO 절감 효과를 숫자로 증명
        - 📄 임원 보고용 EA Cookbook 즉시 생성
        """
    target_persona_en = """
        **Target Persona**
        - 🏢 CIO of Mid-sized Manufacturing
        - 📦 15+ years on ECC 6.0
        - 🔧 High complexity due to Z-code
        - 💰 Evaluating Cloud Migration

        **Value of this tool**
        - ⏱️ Initial assessment in 1 minute
        - 📊 Auto-calculated Clean Core Score
        - 💹 TCO savings proven in numbers
        - 📄 Instantly generate EA Cookbook for execs
        """
    st.markdown(_(target_persona_ko, target_persona_en))
    st.divider()
    pack_lang = st.selectbox(
        _("EA Support Pack Language", "EA Support Pack Language"),
        options=["KO", "EN", "ALL"],
        index=0,
    )
    support_zip = _build_support_pack_zip(pack_lang)
    st.download_button(
        label=_("📦 Download EA Support Pack", "📦 Download EA Support Pack"),
        data=support_zip,
        file_name=f"EA_Support_Pack_{pack_lang}.zip",
        mime="application/zip",
        width="stretch",
    )


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

    st.markdown(
        "<h1 style='text-align:center;'>🏗️ RISE with SAP: Clean Core Assessment</h1>"
        "<p style='text-align:center; color:gray;'>"
        + _("AI 기반 SAP 레거시 시스템 진단 및 전환 전략 도우미", "AI-driven SAP Legacy System Assessment & Strategy Assistant") +
        "</p>",
        unsafe_allow_html=True,
    )

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

    with st.spinner(_("🔄 AI가 SAP Clean Core 분석을 수행하고 있습니다... (약 30-60초 소요)", "🔄 AI is performing Clean Core Analysis... (Approx. 30-60s)")):
        try:
            policy = get_locked_analysis_policy()
            # Fetch strings in requested language
            lang = st.session_state.get("ui_lang", "KO").lower()
            analysis_result = run_analysis(customer_input, policy=policy, lang=lang)
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
                    _("분석 중 오류가 발생했습니다.\n\n선택한 LLM provider API 키가 .env 파일에 설정되어 있는지 확인하세요.",
                      "An error occurred during analysis.\n\nPlease check if LLM provider API key is set in .env file.")
                )
            else:
                st.error(_("분석 중 오류가 발생했습니다. 네트워크 상태 또는 API 한도를 확인하세요.", "An error occurred during analysis. Check network or API limits."))
                if err_msg:
                    st.caption(_(f"상세 오류: {err_msg}", f"Error Details: {err_msg}"))
            return

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
