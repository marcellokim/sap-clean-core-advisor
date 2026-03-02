import streamlit as st
from typing import Callable
from models.schemas import GapAnalysisOutput

def render_joule_checklist(generate_gap_analysis_callback: Callable[[list[str], list[str]], None]) -> None:
    """Joule Readiness Checklist 탭 렌더링"""
    
    st.subheader("🤖 SAP Joule Activation Readiness Checklist")
    st.markdown("SAP S/4HANA Private Cloud 환경에서 Joule을 활성화하기 위한 사전 체크리스트입니다. 체크리스트를 기반으로 Readiness Gap Analysis 리포트를 생성할 수 있습니다.")

    checklist_items = {
        "1. 사전 조건 (Prerequisites)": [
            "대상 시스템 버전 및 SP(Support Package) 레벨이 Joule 요구사항을 충족하는지 확인 완료",
            "BTP Global Account 및 Subaccount 준비 및 Entitlements 확인 완료",
            "SAP Cloud Identity Services (IAS/IPS) 테넌트 준비 완료"
        ],
        "2. 권한 및 보안 (Security & Roles)": [
            "Joule 관리자 및 최종 사용자 역할(Role) 정의 및 매핑 완료",
            "사용자 데이터 및 프롬프트 로깅/감사(Audit) 정책 수립 완료",
            "테스트를 위한 별도의 테스트 사용자/권한 그룹 분리 완료"
        ],
        "3. 연결 및 연동 (Connectivity)": [
            "S/4HANA 시스템과 BTP 간의 Cloud Connector 설정 및 Trust 구성 완료",
            "Destination 설정 및 엔드포인트 연결 테스트(Ping) 정상 확인",
            "SSO(Single Sign-On) 연동 및 토큰 교환 정상 작동 확인"
        ],
        "4. 테스트 및 검증 (Testing)": [
            "인사(HR), 재무(FI) 등 대표적인 비즈니스 시나리오 기반 프롬프트 테스트 완료",
            "다국어(한국어/영어) 질의응답 품질 및 정확도 검증 완료",
            "시스템 장애 또는 응답 지연 시의 Fallback 프로세스 확인 완료"
        ]
    }

    # 상태 관리를 위한 세션 스테이트 초기화
    if "joule_checklist_state" not in st.session_state:
        st.session_state.joule_checklist_state = {
            category: {item: False for item in items}
            for category, items in checklist_items.items()
        }

    total_items = sum(len(items) for items in checklist_items.values())
    
    checked_items_list = []
    unchecked_items_list = []

    # UI 렌더링
    for category, items in checklist_items.items():
        st.markdown(f"#### {category}")
        for item in items:
            # st.checkbox를 사용하고 상태를 업데이트
            is_checked = st.checkbox(
                item, 
                value=st.session_state.joule_checklist_state[category][item],
                key=f"joule_chk_{item}"
            )
            st.session_state.joule_checklist_state[category][item] = is_checked
            
            if is_checked:
                checked_items_list.append(item)
            else:
                unchecked_items_list.append(item)
        st.divider()

    checked_count = len(checked_items_list)
    progress_val = checked_count / total_items if total_items > 0 else 0.0

    st.progress(progress_val, text=f"Readiness Progress: {checked_count} / {total_items} ({(progress_val * 100):.0f}%)")

    # Gap 분석 버튼
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔍 미체크 항목 기반 Gap Analysis 리포트 생성", type="primary", use_container_width=True):
        if not unchecked_items_list:
            st.success("모든 준비가 완료되었습니다! 완벽한 상태입니다.")
        else:
            generate_gap_analysis_callback(checked_items_list, unchecked_items_list)
