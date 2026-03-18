"""Joule readiness checklist rendering."""

from __future__ import annotations

from collections.abc import Callable

import streamlit as st

from ui.locales import _
from ui.styles import render_section_heading


def _checklist_copy() -> dict[str, str]:
    """Return localized shell copy for the Joule readiness checklist."""
    return {
        "eyebrow": "Readiness checklist",
        "title": _("SAP Joule readiness checklist", "SAP Joule readiness checklist"),
        "description": _(
            "SAP S/4HANA Private Cloud 환경에서 Joule 활성화를 준비할 때 필요한 선행 조건을 정리합니다.",
            "Track the prerequisite work needed before activating Joule in an SAP S/4HANA Private Cloud landscape.",
        ),
        "progress_title": _("준비 진행률", "Readiness progress"),
        "progress_note": _(
            "체크된 항목을 기준으로 Gap Analysis 리포트의 우선순위가 정리됩니다.",
            "Checked items determine the focus of the readiness gap analysis.",
        ),
        "completion_label": _("완료율", "Completion"),
        "progress_text": _("완료 항목 {}/{}", "Completed {}/{}"),
        "button_label": _("미체크 항목 기반 Gap Analysis 생성", "Generate gap analysis from unchecked items"),
        "all_done_message": _(
            "모든 준비가 완료되었습니다. 추가 Gap Analysis 없이 바로 실행 계획을 검토할 수 있습니다.",
            "All readiness items are complete. You can move directly to execution planning without an additional gap analysis.",
        ),
    }


def _checklist_sections() -> list[dict[str, object]]:
    """Return localized Joule readiness workstreams and checklist items."""
    return [
        {
            "key": "prerequisites",
            "title": _("사전 조건", "Prerequisites"),
            "description": _(
                "기본 플랫폼, 계정, 테넌트 준비 상태를 확인합니다.",
                "Confirm the core platform, account, and tenant prerequisites.",
            ),
            "items": [
                {
                    "key": "system_version",
                    "label": _(
                        "대상 시스템 버전 및 SP 레벨이 Joule 요구사항을 충족하는지 확인 완료",
                        "Confirmed that the target system version and support package meet Joule requirements",
                    ),
                },
                {
                    "key": "btp_account",
                    "label": _(
                        "BTP Global Account, Subaccount, Entitlements 준비 완료",
                        "Prepared the BTP Global Account, Subaccount, and required entitlements",
                    ),
                },
                {
                    "key": "identity_services",
                    "label": _(
                        "SAP Cloud Identity Services (IAS/IPS) 테넌트 준비 완료",
                        "Prepared the SAP Cloud Identity Services (IAS/IPS) tenant",
                    ),
                },
            ],
        },
        {
            "key": "security_roles",
            "title": _("권한 및 보안", "Security and roles"),
            "description": _(
                "역할, 감사, 테스트 사용자 운영 방식을 정의합니다.",
                "Define the operating model for roles, audit, and test users.",
            ),
            "items": [
                {
                    "key": "role_mapping",
                    "label": _(
                        "Joule 관리자 및 최종 사용자 역할 정의와 매핑 완료",
                        "Defined and mapped Joule administrator and end-user roles",
                    ),
                },
                {
                    "key": "audit_policy",
                    "label": _(
                        "사용자 데이터 및 프롬프트 로깅/감사 정책 수립 완료",
                        "Established the policy for user-data and prompt logging or audit",
                    ),
                },
                {
                    "key": "test_users",
                    "label": _(
                        "테스트용 사용자와 권한 그룹을 운영 계정과 분리 완료",
                        "Separated test users and permission groups from production identities",
                    ),
                },
            ],
        },
        {
            "key": "connectivity",
            "title": _("연결 및 연동", "Connectivity"),
            "description": _(
                "Cloud Connector, destination, SSO 흐름을 검증합니다.",
                "Validate Cloud Connector, destination, and SSO flows.",
            ),
            "items": [
                {
                    "key": "cloud_connector",
                    "label": _(
                        "S/4HANA 시스템과 BTP 간 Cloud Connector 및 trust 구성 완료",
                        "Completed Cloud Connector and trust configuration between S/4HANA and BTP",
                    ),
                },
                {
                    "key": "destination_test",
                    "label": _(
                        "Destination 설정과 엔드포인트 연결 테스트 정상 확인",
                        "Validated destination configuration and endpoint connectivity tests",
                    ),
                },
                {
                    "key": "sso_token",
                    "label": _(
                        "SSO 연동과 토큰 교환이 정상 동작하는지 확인 완료",
                        "Confirmed that SSO integration and token exchange work as expected",
                    ),
                },
            ],
        },
        {
            "key": "testing",
            "title": _("테스트 및 검증", "Testing and validation"),
            "description": _(
                "대표 시나리오, 다국어 품질, 장애 대응 방식을 확인합니다.",
                "Check representative scenarios, multilingual quality, and fallback handling.",
            ),
            "items": [
                {
                    "key": "business_prompts",
                    "label": _(
                        "대표 비즈니스 시나리오 기반 프롬프트 테스트 완료",
                        "Completed prompt tests for representative business scenarios",
                    ),
                },
                {
                    "key": "multilingual_quality",
                    "label": _(
                        "한국어/영어 질의응답 품질과 정확도 검증 완료",
                        "Validated multilingual response quality and accuracy in Korean and English",
                    ),
                },
                {
                    "key": "fallback_process",
                    "label": _(
                        "장애 또는 응답 지연 시 fallback 프로세스 확인 완료",
                        "Confirmed the fallback process for outages or response delays",
                    ),
                },
            ],
        },
    ]


def render_joule_checklist(generate_gap_analysis_callback: Callable[[list[str], list[str]], None]) -> None:
    """Render the Joule readiness checklist and launch the gap analysis callback."""
    copy = _checklist_copy()
    sections = _checklist_sections()

    if "joule_checklist_state" not in st.session_state:
        st.session_state["joule_checklist_state"] = {
            section["key"]: {item["key"]: False for item in section["items"]}
            for section in sections
        }

    state: dict[str, dict[str, bool]] = st.session_state["joule_checklist_state"]
    total_items = sum(len(section["items"]) for section in sections)
    checked_items_list: list[str] = []
    unchecked_items_list: list[str] = []

    render_section_heading(
        eyebrow=copy["eyebrow"],
        title=copy["title"],
        description=copy["description"],
    )

    for section in sections:
        section_state = state.setdefault(
            section["key"],
            {item["key"]: False for item in section["items"]},
        )
        for item in section["items"]:
            section_state.setdefault(item["key"], False)
            if section_state[item["key"]]:
                checked_items_list.append(item["label"])
            else:
                unchecked_items_list.append(item["label"])

    checked_count = len(checked_items_list)
    progress_val = checked_count / total_items if total_items > 0 else 0.0

    with st.container(border=True):
        summary_col, metric_col = st.columns([1.6, 1])
        with summary_col:
            render_section_heading(
                eyebrow="Progress",
                title=copy["progress_title"],
                description=copy["progress_note"],
            )
        with metric_col:
            st.metric(copy["completion_label"], f"{progress_val * 100:.0f}%", copy["progress_text"].format(checked_count, total_items))
        st.progress(progress_val, text=copy["progress_text"].format(checked_count, total_items))

    col1, col2 = st.columns(2)
    for idx, section in enumerate(sections):
        target_col = col1 if idx % 2 == 0 else col2
        with target_col:
            with st.container(border=True):
                render_section_heading(
                    eyebrow="Workstream",
                    title=section["title"],
                    description=section["description"],
                )
                for item in section["items"]:
                    checkbox_key = f"joule_chk_{section['key']}_{item['key']}"
                    is_checked = st.checkbox(
                        item["label"],
                        value=state[section["key"]][item["key"]],
                        key=checkbox_key,
                    )
                    state[section["key"]][item["key"]] = is_checked

    refreshed_checked: list[str] = []
    refreshed_unchecked: list[str] = []
    for section in sections:
        for item in section["items"]:
            if state[section["key"]][item["key"]]:
                refreshed_checked.append(item["label"])
            else:
                refreshed_unchecked.append(item["label"])

    if st.button(copy["button_label"], type="primary", use_container_width=True):
        if not refreshed_unchecked:
            st.success(copy["all_done_message"])
        else:
            generate_gap_analysis_callback(refreshed_checked, refreshed_unchecked)
