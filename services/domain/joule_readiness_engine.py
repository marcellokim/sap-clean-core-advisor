"""Deterministic Joule readiness gap analysis helpers."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from models.schemas import GapAnalysisOutput

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


@dataclass(frozen=True)
class _GapCategory:
    key: str
    title: str
    keywords: tuple[str, ...]
    action: str
    critical: bool = False


_CATEGORIES: tuple[_GapCategory, ...] = (
    _GapCategory(
        key="system_version",
        title="시스템 버전/SP 요구사항",
        keywords=("버전", "sp", "support package", "요구사항", "system version"),
        action="대상 S/4HANA 릴리스와 SP 레벨을 Joule 요구사항표에 대조하고 부족분 업그레이드 일정을 확정합니다.",
        critical=True,
    ),
    _GapCategory(
        key="btp_account",
        title="BTP 계정 및 entitlement",
        keywords=("btp", "global account", "subaccount", "entitlement", "서브어카운트"),
        action="BTP Global Account, Subaccount, entitlement 소유자와 승인 경로를 확정합니다.",
        critical=True,
    ),
    _GapCategory(
        key="identity",
        title="Identity/SSO 신뢰 구성",
        keywords=("identity", "ias", "ips", "sso", "token", "토큰", "trust", "신뢰", "테넌트"),
        action="IAS/IPS 테넌트, SSO, 토큰 교환을 통합 테스트 계정으로 end-to-end 검증합니다.",
        critical=True,
    ),
    _GapCategory(
        key="security_roles",
        title="권한 및 감사 정책",
        keywords=("권한", "역할", "role", "audit", "감사", "logging", "로그", "보안"),
        action="Joule 관리자/최종 사용자 역할 매트릭스와 감사 로그 보존 정책을 승인받습니다.",
        critical=True,
    ),
    _GapCategory(
        key="connectivity",
        title="연결 및 destination 검증",
        keywords=("cloud connector", "destination", "endpoint", "엔드포인트", "연결", "커넥터"),
        action="Cloud Connector, destination, 엔드포인트 연결을 운영망과 유사한 조건에서 재검증합니다.",
        critical=True,
    ),
    _GapCategory(
        key="testing",
        title="시나리오 테스트 및 fallback",
        keywords=("prompt", "프롬프트", "테스트", "다국어", "multilingual", "fallback", "응답 지연", "품질"),
        action="대표 업무 프롬프트, 한국어/영어 응답 품질, 장애 fallback 절차를 리허설합니다.",
    ),
)


def build_gap_analysis_prompt(checked_items: list[str], unchecked_items: list[str]) -> str:
    """Build the provider prompt from checklist state."""
    return GAP_ANALYSIS_PROMPT.format(
        checked="\n".join(f"- {item}" for item in checked_items) if checked_items else "없음",
        unchecked="\n".join(f"- {item}" for item in unchecked_items) if unchecked_items else "없음",
    )


def _category_for_item(item: str) -> _GapCategory:
    normalized = item.casefold()
    for category in _CATEGORIES:
        if any(keyword.casefold() in normalized for keyword in category.keywords):
            return category
    return _CATEGORIES[-1]


def _risk_level(unchecked_count: int, categories: list[_GapCategory]) -> str:
    if unchecked_count <= 0:
        return "Low"
    critical_count = sum(1 for category in categories if category.critical)
    if unchecked_count >= 6 or critical_count >= 1:
        return "High"
    if unchecked_count >= 3:
        return "Medium"
    return "Low"


def build_deterministic_gap_analysis(
    checked_items: list[str],
    unchecked_items: list[str],
    *,
    reason: str | None = None,
) -> GapAnalysisOutput:
    """Return a deterministic Joule gap analysis when LLM output is unavailable."""
    if not unchecked_items:
        summary_prefix = f"{reason} " if reason else ""
        return GapAnalysisOutput(
            identified_gaps=[],
            recommended_actions=["완료된 준비 항목을 기준으로 운영 전환 체크리스트와 담당자 승인 로그를 보관합니다."],
            risk_level="Low",
            executive_summary=(
                f"{summary_prefix}현재 체크리스트상 미완료 항목은 없습니다. "
                "활성화 전 최종 승인, 테스트 증적, 운영 fallback 절차만 재확인하면 됩니다."
            ).strip(),
        )

    categories = [_category_for_item(item) for item in unchecked_items]
    counts = Counter(category.key for category in categories)
    by_key = {category.key: category for category in _CATEGORIES}
    ordered_categories = sorted(
        (by_key[key] for key in counts),
        key=lambda category: (not category.critical, -counts[category.key], category.title),
    )

    identified_gaps = [
        f"{category.title}: 미완료 항목 {counts[category.key]}건이 남아 있어 Joule 활성화 전 선행 검증이 필요합니다."
        for category in ordered_categories[:3]
    ]
    recommended_actions = [category.action for category in ordered_categories[:5]]
    risk_level = _risk_level(len(unchecked_items), categories)
    reason_sentence = f"{reason} " if reason else ""
    executive_summary = (
        f"{reason_sentence}총 {len(unchecked_items)}개 미완료 항목이 남아 있으며, "
        f"주요 갭은 {', '.join(category.title for category in ordered_categories[:3])}입니다. "
        f"현재 readiness 리스크는 {risk_level}로 판단되며, 핵심 인프라와 권한/연결 검증을 먼저 닫아야 합니다."
    ).strip()

    return GapAnalysisOutput(
        identified_gaps=identified_gaps,
        recommended_actions=recommended_actions,
        risk_level=risk_level,
        executive_summary=executive_summary,
    )
