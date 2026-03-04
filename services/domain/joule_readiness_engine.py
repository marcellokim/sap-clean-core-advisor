import json
import logging
from typing import Any

from models.schemas import GapAnalysisOutput
from services.infrastructure.llm.gemini_provider import GeminiLLMProvider
from config.settings import settings

logger = logging.getLogger(__name__)

GAP_ANALYSIS_SYSTEM = """\
당신은 SAP BTP 및 S/4HANA Private Cloud 도입을 담당하는 수석 Enterprise Architect입니다.
고객이 제출한 Joule Activation 사전 점검 체크리스트의 '완료되지 않은(미체크) 항목'들을 분석하여 Gap Analysis 보고서를 작성해야 합니다.

출력은 반드시 요구된 JSON 스키마를 준수해야 합니다.
"""

GAP_ANALYSIS_PROMPT = """\
## 고객 점검 상태
아래는 고객이 점검을 완료한 항목과, 아직 완료하지 못한 항목의 목록입니다.

[완료된 항목]
{checked}

[미완료(Gap) 항목]
{unchecked}

## 요구사항
위 정보를 바탕으로 아래 구조화된 JSON 형태로 Gap Analysis 결과를 도출하세요.
1. identified_gaps: 미완료 항목들을 분석하여 근본적인 결함이나 리스크를 2~3가지로 요약
2. recommended_actions: 각 Gap을 해소하기 위해 당장 실행해야 할 구체적 조치 3~5가지 (예: "BTP Global Account 권한 확보", "Cloud Identity 연동 가이드 배포" 등)
3. risk_level: "High", "Medium", "Low" 중 1개 선택 (미완료가 많거나 핵심 인프라 항목이면 High)
4. executive_summary: 경영진/임원에게 보고할 3~5문장 길이의 명확한 요약

출력은 반드시 JSON 형식만을 반환하세요 (마크다운 포맷팅 ```json 없이).
"""

import streamlit as st

@st.cache_data(ttl=3600, show_spinner=False)
def generate_joule_gap_analysis(checked_items: list[str], unchecked_items: list[str]) -> GapAnalysisOutput:
    """LLM을 호출하여 미체크 항목 기반 갭 분석 리포트를 생성합니다."""
    
    prompt = GAP_ANALYSIS_PROMPT.format(
        checked="\\n".join(f"- {i}" for i in checked_items) if checked_items else "없음",
        unchecked="\\n".join(f"- {i}" for i in unchecked_items) if unchecked_items else "없음"
    )
    
    # 간소화를 위해 기본 Gemini Provider 직접 호출
    provider = GeminiLLMProvider()
    
    # JSON 모드를 강제하기 위해 시스템 프롬프트와 Response Schema 명시
    # (GeminiLLMProvider 내부 메서드를 직접 사용합니다)
    schema_dict = GapAnalysisOutput.model_json_schema()
    
    # Provider의 Base 로직을 활용
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        from pydantic import BaseModel
        
        # Pydantic v2 호환성을 위해 with_structured_output이 안전하게 파싱할 수 있도록 설정
        llm = ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            api_key=settings.GOOGLE_API_KEY,  # google_api_key -> api_key 로 변경
            temperature=0.2,
        ).with_structured_output(GapAnalysisOutput)
        
        from langchain_core.messages import SystemMessage, HumanMessage
        messages = [
            SystemMessage(content=GAP_ANALYSIS_SYSTEM),
            HumanMessage(content=prompt)
        ]
        
        result_model = llm.invoke(messages)
        # return_type = BaseModel이므로 바로 반환 가능
        return result_model
    except Exception as e:
        logger.error(f"Gap Analysis LLM 호출 실패: {e}")
        # 오류 발생 시 Fallback 데이터 제공
        return GapAnalysisOutput(
            identified_gaps=["AI 분석 실패로 확인할 수 없음. 사용자가 체크하지 않은 모든 항목을 리스크로 간주함."],
            recommended_actions=["체크리스트의 모든 미체크 항목을 순차적으로 수행할 것."],
            risk_level="High",
            executive_summary="현재 AI 분석 모듈에 연결할 수 없어 상세 갭 분석을 수행하지 못했습니다. 수동으로 미체크 항목을 점검하시기 바랍니다."
        )
