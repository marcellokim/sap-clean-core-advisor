"""고객사 레거시 시스템 프로파일 입력 폼 (Streamlit)."""

from __future__ import annotations

import streamlit as st

from models.schemas import CustomerInput, ModuleInfo

# ────────────────────────────────────────────────────────────────────
# 선택지 상수
# ────────────────────────────────────────────────────────────────────
INDUSTRIES = [
    "제조", "유통/리테일", "금융/보험", "화학/에너지",
    "건설/엔지니어링", "통신/IT", "공공/공기업", "의료/제약", "기타",
]

ERP_VERSIONS = [
    "S/4HANA 2023", "S/4HANA 2021", "S/4HANA 2020", "S/4HANA",
    "ECC 6.0 EHP8", "ECC 6.0 EHP7", "ECC 6.0", "ECC 5.0", "R/3 4.7",
]

DB_TYPES = [
    "SAP HANA", "Oracle", "Microsoft SQL Server", "IBM DB2", "MaxDB",
]

SAP_MODULES = [
    "FI", "CO", "MM", "SD", "PP", "HR", "PM", "QM", "WM", "PS",
]

MODULE_LABELS: dict[str, str] = {
    "FI": "FI – Financial Accounting",
    "CO": "CO – Controlling",
    "MM": "MM – Materials Management",
    "SD": "SD – Sales & Distribution",
    "PP": "PP – Production Planning",
    "HR": "HR – Human Resources",
    "PM": "PM – Plant Maintenance",
    "QM": "QM – Quality Management",
    "WM": "WM – Warehouse Management",
    "PS": "PS – Project System",
}

CUSTOMIZATION_LEVELS = {
    "Low (표준 위주)": "low",
    "Medium (일부 커스텀)": "medium",
    "High (대규모 커스텀)": "high",
}


def render_input_form() -> CustomerInput | None:
    """Streamlit 입력 폼을 렌더링하고, 제출 시 CustomerInput을 반환."""
    st.markdown(
        """
        <h2 style='margin-bottom: 0;'>📋 Legacy System Profile</h2>
        <p style='color: gray; margin-top: 4px;'>
        고객사의 현재 SAP ERP 환경 정보를 입력하세요.
        정확한 데이터일수록 분석 결과의 신뢰도가 높아집니다.
        </p>
        """,
        unsafe_allow_html=True,
    )

    with st.form("customer_input_form"):
        # ── 기본 정보 ──
        st.subheader("기업 정보")
        col1, col2 = st.columns(2)
        with col1:
            company_name = st.text_input(
                "회사명", placeholder="예: (주)한국제조"
            )
            industry = st.selectbox("업종", INDUSTRIES)
        with col2:
            annual_it_budget = st.number_input(
                "연간 IT 예산 (억원)", min_value=0.0, value=50.0, step=5.0
            )
            migration_timeline = st.slider(
                "희망 전환 기간 (개월)", min_value=3, max_value=48, value=18
            )

        st.divider()

        # ── 시스템 정보 ──
        st.subheader("SAP 시스템 현황")
        col3, col4 = st.columns(2)
        with col3:
            erp_version = st.selectbox("ERP 버전", ERP_VERSIONS, index=6)
            db_type = st.selectbox("데이터베이스", DB_TYPES, index=1)
            db_size = st.number_input(
                "DB 사이즈 (GB)", min_value=1.0, value=500.0, step=100.0
            )
        with col4:
            num_users = st.number_input(
                "사용자 수", min_value=1, value=800, step=50
            )
            num_custom_programs = st.number_input(
                "커스텀 프로그램(Z-code) 수", min_value=0, value=350, step=50
            )
            custom_code_ratio = st.slider(
                "커스텀 코드 비중 (%)", min_value=0, max_value=100, value=45
            )

        st.divider()

        # ── 모듈 정보 ──
        st.subheader("사용 모듈 & 커스텀 심각도")
        st.caption(
            "사용 중인 모듈을 선택하고, 각 모듈의 커스텀 수준을 지정하세요."
        )

        selected_modules = st.multiselect(
            "사용 중인 SAP 모듈",
            options=SAP_MODULES,
            default=["FI", "CO", "MM", "SD"],
            format_func=lambda x: MODULE_LABELS.get(x, x),
        )

        module_infos: list[dict[str, str]] = []
        if selected_modules:
            cols = st.columns(min(len(selected_modules), 4))
            for idx, mod_name in enumerate(selected_modules):
                with cols[idx % len(cols)]:
                    level_label = st.selectbox(
                        f"{mod_name} 커스텀 수준",
                        options=list(CUSTOMIZATION_LEVELS.keys()),
                        index=1,
                        key=f"mod_{mod_name}",
                    )
                    module_infos.append({
                        "module_name": mod_name,
                        "customization_level": CUSTOMIZATION_LEVELS[level_label],
                    })

        st.divider()

        # ── 고충사항 ──
        st.subheader("주요 고충사항")
        pain_points = st.text_area(
            "현재 시스템 운영 시 겪고 있는 어려움을 자유롭게 기술하세요.",
            placeholder=(
                "예: 매월 결산에 5일 이상 소요, 경영진의 클라우드/AI 도입 압박, "
                "시스템 업그레이드 시 커스텀 코드 호환성 문제 빈발..."
            ),
            height=100,
        )

        # ── 제출 ──
        submitted = st.form_submit_button(
            "🔍 Clean Core 분석 시작",
            type="primary",
            use_container_width=True,
        )

        if submitted:
            # 유효성 검증
            if not company_name.strip():
                st.error("회사명을 입력해 주세요.")
                return None
            if not selected_modules:
                st.error("최소 1개 이상의 SAP 모듈을 선택해 주세요.")
                return None

            modules = [ModuleInfo(**info) for info in module_infos]
            return CustomerInput(
                company_name=company_name.strip(),
                industry=industry,
                erp_version=erp_version,
                db_type=db_type,
                db_size_gb=db_size,
                num_users=num_users,
                num_custom_programs=num_custom_programs,
                custom_code_ratio=float(custom_code_ratio),
                modules=modules,
                annual_it_budget_krw=annual_it_budget,
                pain_points=pain_points,
                migration_timeline_months=migration_timeline,
            )

    return None
