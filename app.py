"""SAP Clean Core Advisor – 메인 Streamlit 앱.

입력 → 규칙 기반 계산 → AI 분석(RAG) → 시각화 → PDF 다운로드 전체 플로우를 통합합니다.
"""

import io
import os
import zipfile
from pathlib import Path

import streamlit as st

from models.schemas import CustomerInput
from services.analysis_service import analyze_customer_input
from ui.dashboard import render_dashboard
from ui.input_form import render_input_form

DOCS_ROOT = Path(__file__).resolve().parent / "docs"


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
    st.image(
        "https://upload.wikimedia.org/wikipedia/commons/5/59/SAP_2011_logo.svg",
        width=120,
    )
    st.markdown("## RISE with SAP")
    st.markdown("### Clean Core Assessment\n& TCO Simulator")
    st.divider()
    st.markdown(
        """
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
    )
    st.divider()
    pack_lang = st.selectbox(
        "EA Support Pack Language",
        options=["KO", "EN", "ALL"],
        index=0,
    )
    support_zip = _build_support_pack_zip(pack_lang)
    st.download_button(
        label="📦 Download EA Support Pack",
        data=support_zip,
        file_name=f"EA_Support_Pack_{pack_lang}.zip",
        mime="application/zip",
        width="stretch",
    )
    st.divider()
    st.caption(
        "Built with Streamlit • LangChain • Gemini • ChromaDB\n\n"
        "Reducing complexity and operational costs\n"
        "through intelligent automation."
    )


# ────────────────────────────────────────────────────────────────────
# 메인 영역
# ────────────────────────────────────────────────────────────────────
def main() -> None:
    """메인 앱 플로우."""
    st.markdown(
        "<h1 style='text-align:center;'>🏗️ RISE with SAP: Clean Core Assessment</h1>"
        "<p style='text-align:center; color:gray;'>"
        "AI 기반 SAP 레거시 시스템 진단 및 전환 전략 도우미</p>",
        unsafe_allow_html=True,
    )

    # ── 입력 폼 ──
    customer_input: CustomerInput | None = render_input_form()

    if customer_input is None:
        # 입력 전 안내
        st.markdown("---")
        st.info(
            "👆 위 폼에 고객사 정보를 입력하고 **'Clean Core 분석 시작'** 버튼을 눌러주세요.\n\n"
            "분석 결과로 다음을 제공합니다:\n"
            "- **Clean Core Score** (0-100) – 현재 시스템의 표준 준수도\n"
            "- **기술 부채 히트맵** – 모듈별 커스텀 부채 시각화\n"
            "- **TCO 비교 분석** – 현재 vs 전환 후 비용 비교\n"
            "- **AI 기반 진단 리포트** – 리스크 평가 및 전환 전략\n"
            "- **EA Cookbook PDF** – 임원 보고용 문서 자동 생성"
        )
        return

    # ── 분석 실행 ──
    with st.spinner("🔄 AI가 SAP Clean Core 분석을 수행하고 있습니다... (약 30-60초 소요)"):
        try:
            analysis_result = analyze_customer_input(customer_input)
            output = analysis_result.output
            pdf_bytes = analysis_result.pdf_bytes
        except Exception as e:
            err_msg = str(e).strip()
            if not os.getenv("GOOGLE_API_KEY", "").strip():
                st.error(
                    "분석 중 오류가 발생했습니다.\n\n"
                    "GOOGLE_API_KEY가 .env 파일에 설정되어 있는지 확인하세요."
                )
            else:
                st.error(
                    "분석 중 오류가 발생했습니다. 네트워크 상태 또는 API 한도를 확인하세요."
                )
                if err_msg:
                    st.caption(f"상세 오류: {err_msg}")
            return

    # ── PDF 생성 결과 안내 ──
    if analysis_result.pdf_error_code:
        st.warning(
            "PDF 생성에 실패하여 화면 결과만 제공합니다. "
            f"(코드: {analysis_result.pdf_error_code})"
        )
        if analysis_result.pdf_error_message:
            st.caption(f"PDF 오류 상세: {analysis_result.pdf_error_message}")

    # ── 결과 저장 (session_state) ──
    st.session_state["last_output"] = output
    st.session_state["last_input"] = customer_input
    st.session_state["last_pdf"] = pdf_bytes

    # ── 대시보드 렌더링 ──
    render_dashboard(output, customer_input, pdf_bytes)


if __name__ == "__main__":
    main()
