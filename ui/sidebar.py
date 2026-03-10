"""Sidebar rendering and support-pack download helpers."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import streamlit as st

from ui.locales import _


def _build_support_pack_zip(docs_root: Path, language_mode: str) -> bytes:
    include_all = language_mode == "ALL"
    language_suffix = f"_{language_mode}.md"
    candidates: list[Path] = []
    for folder in ("workshop-kit", "joule-playbook", "ops-toolkit", "ea-cookbook"):
        folder_path = docs_root / folder
        if not folder_path.exists():
            continue
        for path in sorted(folder_path.glob("*")):
            if path.is_dir():
                continue
            name = path.name
            if include_all:
                candidates.append(path)
            elif name.endswith(language_suffix) or ("_KO" not in name and "_EN" not in name):
                candidates.append(path)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in candidates:
            arcname = str(path.relative_to(docs_root.parent))
            zf.write(path, arcname=arcname)
    return buf.getvalue()


def render_sidebar(logo_path: Path, docs_root: Path) -> None:
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

    with st.sidebar:
        if logo_path.exists():
            st.image(str(logo_path), width=120)
        else:
            st.markdown("### SAP")

        st.markdown("## RISE with SAP")
        st.markdown("### Clean Core Assessment\n& TCO Simulator")
        st.divider()

        ui_lang = st.selectbox("UI Language / 언어", options=["KO", "EN"], index=0)
        st.session_state["ui_lang"] = ui_lang

        st.markdown(_(target_persona_ko, target_persona_en))
        st.divider()
        pack_lang = st.selectbox(
            _("EA Support Pack Language", "EA Support Pack Language"),
            options=["KO", "EN", "ALL"],
            index=0,
        )
        support_zip = _build_support_pack_zip(docs_root, pack_lang)
        st.download_button(
            label=_("📦 Download EA Support Pack", "📦 Download EA Support Pack"),
            data=support_zip,
            file_name=f"EA_Support_Pack_{pack_lang}.zip",
            mime="application/zip",
            width="stretch",
        )
