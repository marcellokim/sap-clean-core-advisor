"""고객사 레거시 시스템 프로파일 입력 폼 (Streamlit)."""

from __future__ import annotations

import streamlit as st

from models.schemas import CustomerInput, ModuleInfo
from ui.locales import _

# ────────────────────────────────────────────────────────────────────
# 선택지 상수
# ────────────────────────────────────────────────────────────────────
INDUSTRIES_KO = [
    "제조", "유통/리테일", "금융/보험", "화학/에너지",
    "건설/엔지니어링", "통신/IT", "공공/공기업", "의료/제약", "기타",
]
INDUSTRIES_EN = [
    "Manufacturing", "Retail", "Finance", "Chemical/Energy",
    "Construction/Engineering", "Telco/IT", "Public", "Healthcare", "Other",
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

CUSTOMIZATION_LEVELS_KO = {
    "Low (표준 위주)": "low",
    "Medium (일부 커스텀)": "medium",
    "High (대규모 커스텀)": "high",
}
CUSTOMIZATION_LEVELS_EN = {
    "Low (Standard)": "low",
    "Medium (Some custom)": "medium",
    "High (Heavy custom)": "high",
}


def render_input_form() -> CustomerInput | None:
    """Streamlit 입력 폼을 렌더링하고, 제출 시 CustomerInput을 반환."""
    st.markdown(
        _("<h2 style='margin-bottom: 0;'>📋 Legacy System Profile</h2>"
          "<p style='color: gray; margin-top: 4px;'>"
          "고객사의 현재 SAP ERP 환경 정보를 입력하세요.<br>"
          "정확한 데이터일수록 분석 결과의 신뢰도가 높아집니다."
          "</p>",
          "<h2 style='margin-bottom: 0;'>📋 Legacy System Profile</h2>"
          "<p style='color: gray; margin-top: 4px;'>"
          "Enter the current SAP ERP environment details.<br>"
          "Accurate data improves the reliability of the analysis."
          "</p>"),
        unsafe_allow_html=True,
    )

    with st.form("customer_input_form"):
        st.subheader(_("기업 정보", "Company Profile"))
        col1, col2 = st.columns(2)
        with col1:
            company_name = st.text_input(
                _("회사명", "Company Name"), placeholder=_("예: (주)한국제조", "e.g., Contoso Corp")
            )
            industry_val = st.selectbox(_("업종", "Industry"), _(INDUSTRIES_KO, INDUSTRIES_EN))
            industry = INDUSTRIES_KO[INDUSTRIES_EN.index(industry_val)] if isinstance(industry_val, str) and industry_val in INDUSTRIES_EN else industry_val
            
        with col2:
            annual_it_budget = st.number_input(
                _("연간 IT 예산 (억원)", "Annual IT Budget (100M KRW)"), min_value=0.0, value=50.0, step=5.0
            )
            migration_timeline = st.slider(
                _("희망 전환 기간 (개월)", "Desired Migration Timeline (Months)"), min_value=3, max_value=48, value=18
            )

        st.divider()

        st.subheader(_("SAP 시스템 현황", "SAP System Status"))
        col3, col4 = st.columns(2)
        with col3:
            erp_version = st.selectbox(_("ERP 버전", "ERP Version"), ERP_VERSIONS, index=6)
            db_type = st.selectbox(_("데이터베이스", "Database"), DB_TYPES, index=1)
            db_size = st.number_input(
                _("DB 사이즈 (GB)", "DB Size (GB)"), min_value=1.0, value=500.0, step=100.0
            )
        with col4:
            num_users = st.number_input(
                _("사용자 수", "Number of Users"), min_value=1, value=800, step=50
            )
            num_custom_programs = st.number_input(
                _("커스텀 프로그램(Z-code) 수", "Custom Programs (Z-code) Count"), min_value=0, value=350, step=50
            )
            custom_code_ratio = st.slider(
                _("커스텀 코드 비중 (%)", "Custom Code Ratio (%)"), min_value=0, max_value=100, value=45
            )

        st.divider()

        st.subheader(_("사용 모듈 & 커스텀 심각도", "Modules & Customization Severity"))
        st.caption(
            _("사용 중인 모듈을 선택하고, 각 모듈의 커스텀 수준을 지정하세요.",
              "Select modules in use and specify the customization level for each.")
        )

        selected_modules = st.multiselect(
            _("사용 중인 SAP 모듈", "SAP Modules in Use"),
            options=SAP_MODULES,
            default=["FI", "CO", "MM", "SD"],
            format_func=lambda x: MODULE_LABELS.get(x, x),
        )

        module_infos: list[dict[str, str]] = []
        if selected_modules:
            cols = st.columns(min(len(selected_modules), 4))
            for idx, mod_name in enumerate(selected_modules):
                with cols[idx % len(cols)]:
                    level_dict = _(CUSTOMIZATION_LEVELS_KO, CUSTOMIZATION_LEVELS_EN)
                    level_label = st.selectbox(
                        _("{} 커스텀 수준", "{} Custom Level").format(mod_name),
                        options=list(level_dict.keys()),
                        index=1,
                        key=f"mod_{mod_name}",
                    )
                    module_infos.append({
                        "module_name": mod_name,
                        "customization_level": level_dict[level_label],
                    })

        st.divider()

        st.subheader(_("주요 고충사항", "Key Pain Points"))
        pain_points = st.text_area(
            _("현재 시스템 운영 시 겪고 있는 어려움을 자유롭게 기술하세요.",
              "Describe the difficulties you are currently experiencing with system operations."),
            placeholder=_(
                "예: 매월 결산에 5일 이상 소요, 경영진의 클라우드/AI 도입 압박, "
                "시스템 업그레이드 시 커스텀 코드 호환성 문제 빈발...",
                "e.g., Monthly closing takes 5+ days, executive pressure for Cloud/AI adoption, "
                "frequent custom code compatibility issues during upgrades..."
            ),
            height=100,
        )

        submitted = st.form_submit_button(
            _("🔍 Clean Core 분석 시작", "🔍 Start Clean Core Analysis"),
            type="primary",
            use_container_width=True,
        )

        if submitted:
            if not company_name.strip():
                st.error(_("회사명을 입력해 주세요.", "Please enter the company name."))
                return None
            if not selected_modules:
                st.error(_("최소 1개 이상의 SAP 모듈을 선택해 주세요.", "Please select at least one SAP module."))
                return None

            if annual_it_budget <= 0.0:
                st.error(_("연간 IT 예산은 0보다 커야 합니다.", "Annual IT budget must be greater than 0."))
                return None
            
            if num_custom_programs > 0 and custom_code_ratio == 0.0:
                st.error(_("커스텀 프로그램 수가 존재하지만 커스텀 코드 비중이 0%입니다.", "Custom program count is > 0 but custom ratio is 0%."))
                return None
            
            if num_custom_programs == 0 and custom_code_ratio > 0.0:
                st.error(_("커스텀 프로그램 수가 0개인데 커스텀 코드 비중이 0%보다 큽니다.", "Custom program count is 0 but custom ratio is > 0%."))
                return None

            if num_custom_programs > num_users * 100:
                st.warning(_("경고: 사용자 수 대비 커스텀 프로그램 수가 이례적으로 많습니다. 입력값을 확인해 주세요.",
                             "Warning: Custom program count is unusually high compared to user count. Please verify inputs."))
            
            if db_size < 10 and num_users > 1000:
                st.warning(_("경고: 대규모 사용자(1000명 이상) 환경 대비 DB 사이즈(10GB 미만)가 이례적으로 작습니다.",
                             "Warning: DB size (<10GB) is unusually small for a large user base (>1000). Please verify inputs."))

            modules = [ModuleInfo(**info) for info in module_infos]
            return CustomerInput(
                company_name=company_name.strip(),
                industry=str(industry) if industry else "제조",
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
