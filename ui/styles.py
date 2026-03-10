"""UI style helpers for Streamlit app shell."""

from __future__ import annotations

import streamlit as st

GLOBAL_STYLES = """
<style>
    /* 전체 폰트 및 배경색 변경 */
    html, body, [class*="css"] {
        font-family: 'Inter', 'Noto Sans KR', sans-serif !important;
    }
    .stApp {
        background-color: #F8F9FA;
    }

    /* 사이드바 스타일링 */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #E9ECEF;
        padding-top: 2rem;
    }
    [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        color: #0070F2; /* SAP 공식 블루 사용 */
        font-weight: 700;
    }

    /* 메인 타이틀 아름답게 꾸미기 */
    h1 {
        font-weight: 800 !important;
        background: -webkit-linear-gradient(45deg, #0070F2, #00B1F2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        padding-bottom: 5px;
    }

    /* 탭 디자인 오버라이드 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #ffffff;
        padding: 5px 10px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    .stTabs [data-baseweb="tab"] {
        padding-top: 10px;
        padding-bottom: 10px;
        padding-left: 20px;
        padding-right: 20px;
        border-radius: 8px;
        transition: all 0.2s ease-in-out;
    }
    .stTabs [aria-selected="true"] {
        background-color: #EBF5FF !important;
        color: #0070F2 !important;
        font-weight: 700;
    }

    /* 버튼 스타일 (프리미엄 룩) */
    .stButton > button {
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: all 0.2s;
        border: none !important;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 112, 242, 0.2);
    }

    /* 카드형 컨테이너 (위젯 박스) */
    div[data-testid="stExpander"] {
        border: 1px solid #E9ECEF !important;
        border-radius: 12px !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.02) !important;
        background-color: white !important;
    }
    div[data-testid="stExpander"] > summary {
        background-color: #F8F9FA !important;
        border-radius: 12px 12px 0 0 !important;
        font-weight: 600;
    }
</style>
"""


def apply_global_styles() -> None:
    """Apply global Streamlit style overrides."""
    st.markdown(GLOBAL_STYLES, unsafe_allow_html=True)

