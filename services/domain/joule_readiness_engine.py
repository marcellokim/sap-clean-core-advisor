import logging

import streamlit as st

from models.schemas import GapAnalysisOutput
from services.infrastructure.llm.gemini_provider import GeminiLLMProvider

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


def _build_fallback_output() -> GapAnalysisOutput:
    return GapAnalysisOutput(
        identified_gaps=["AI 분석 실패로 확인할 수 없음. 사용자가 체크하지 않은 모든 항목을 리스크로 간주함."],
        recommended_actions=["체크리스트의 모든 미체크 항목을 순차적으로 수행할 것."],
        risk_level="High",
        executive_summary="현재 AI 분석 모듈에 연결할 수 없어 상세 갭 분석을 수행하지 못했습니다. 수동으로 미체크 항목을 점검하시기 바랍니다.",
    )


@st.cache_data(ttl=3600, show_spinner=False)
def generate_joule_gap_analysis(checked_items: list[str], unchecked_items: list[str]) -> GapAnalysisOutput:
    """LLM을 호출하여 미체크 항목 기반 갭 분석 리포트를 생성합니다."""

    prompt = GAP_ANALYSIS_PROMPT.format(
        checked="\\n".join(f"- {i}" for i in checked_items) if checked_items else "없음",
        unchecked="\\n".join(f"- {i}" for i in unchecked_items) if unchecked_items else "없음",
    )

    provider = GeminiLLMProvider()

    try:
        result = provider.generate_structured_output(
            system_prompt=GAP_ANALYSIS_SYSTEM,
            user_prompt=prompt,
            output_model=GapAnalysisOutput,
        )
        return GapAnalysisOutput.model_validate(result)
    except Exception as e:
        logger.error(f"Gap Analysis LLM 호출 실패: {e}")
        return _build_fallback_output()
