"""Sidebar rendering and support-pack download helpers."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path
from typing import Any

import streamlit as st

from ui.locales import _
from ui.styles import render_section_heading


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


def _sidebar_copy() -> dict[str, Any]:
    """Return localized sidebar copy blocks for the redesigned shell."""
    return {
        "product_title": "SAP Clean Core Advisor",
        "product_summary": _(
            "클린 코어 진단, TCO 비교, 실행자료 패키지를 한 화면에서 정리하는 워크스페이스입니다.",
            "A workspace for Clean Core diagnostics, TCO comparison, and executive-ready enablement packs.",
        ),
        "language_label": "UI Language / 언어",
        "persona_title": _("추천 사용 시나리오", "Recommended scenario"),
        "persona_items": [
            _("국내 중견 제조기업 CIO 또는 EA 리드", "CIO or EA lead at a mid-sized manufacturer"),
            _("15년 이상 운영한 ECC 6.0 기반 환경", "ECC 6.0 estate operated for 15+ years"),
            _("복잡한 Z-code와 업그레이드 리스크가 높은 환경", "High Z-code complexity and elevated upgrade risk"),
        ],
        "value_title": _("주요 산출물", "Primary outputs"),
        "value_items": [
            _("Clean Core score와 기술 부채 시각화", "Clean Core score and technical debt visibility"),
            _("현재 대비 전환 후 TCO 비교", "Current-versus-target TCO comparison"),
            _("임원 보고용 EA Cookbook PDF", "Executive-ready EA Cookbook PDF"),
        ],
        "support_title": _("EA support pack", "EA support pack"),
        "support_description": _(
            "워크숍, Joule 준비, 운영 전환에 필요한 문서를 언어별로 묶어 내려받을 수 있습니다.",
            "Download workshop, Joule readiness, and operating-model materials in the language bundle you need.",
        ),
        "support_label": _("EA Support Pack Language", "EA Support Pack Language"),
        "support_button": _("Download EA Support Pack", "Download EA Support Pack"),
    }


def render_sidebar(logo_path: Path, docs_root: Path) -> None:
    copy = _sidebar_copy()

    with st.sidebar:
        if logo_path.exists():
            st.image(str(logo_path), width=132)
        else:
            st.markdown("### SAP")

        st.markdown(f"## {copy['product_title']}")
        st.caption(copy["product_summary"])

        ui_lang = st.selectbox(copy["language_label"], options=["KO", "EN"], index=0)
        st.session_state["ui_lang"] = ui_lang

        with st.container(border=True):
            render_section_heading(
                eyebrow="Audience",
                title=str(copy["persona_title"]),
                description=_(
                    "이 워크스페이스가 가장 큰 가치를 주는 대표 상황입니다.",
                    "The representative situation where this workspace delivers the most value.",
                ),
            )
            st.markdown(
                "<ul class='advisor-muted-list'>"
                + "".join(f"<li>{item}</li>" for item in copy["persona_items"])
                + "</ul>",
                unsafe_allow_html=True,
            )

        with st.container(border=True):
            render_section_heading(
                eyebrow="Outputs",
                title=str(copy["value_title"]),
                description=_(
                    "분석 완료 후 바로 활용할 수 있는 결과물입니다.",
                    "Deliverables available immediately after the assessment completes.",
                ),
            )
            st.markdown(
                "<ul class='advisor-muted-list'>"
                + "".join(f"<li>{item}</li>" for item in copy["value_items"])
                + "</ul>",
                unsafe_allow_html=True,
            )

        with st.container(border=True):
            render_section_heading(
                eyebrow="Resources",
                title=str(copy["support_title"]),
                description=str(copy["support_description"]),
            )
            pack_lang = st.selectbox(
                str(copy["support_label"]),
                options=["KO", "EN", "ALL"],
                index=0,
            )
            support_zip = _build_support_pack_zip(docs_root, pack_lang)
            st.download_button(
                label=str(copy["support_button"]),
                data=support_zip,
                file_name=f"EA_Support_Pack_{pack_lang}.zip",
                mime="application/zip",
                use_container_width=True,
            )
