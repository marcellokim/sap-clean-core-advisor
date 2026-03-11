"""Deterministic pain-point keyword tagging helpers."""

from __future__ import annotations

import re


_CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "financial_close": ("결산", "마감", "closing", "close"),
    "performance": ("성능", "느림", "slow", "latency", "배치", "batch", "응답"),
    "upgrade": ("업그레이드", "upgrade", "호환성", "compatibility", "retrofit", "release"),
    "integration": ("인터페이스", "integration", "api", "edi", "연계", "if "),
    "ai_data": ("ai", "analytics", "분석", "리포트", "report", "데이터", "joule", "copilot", "cloud"),
    "security": ("보안", "감사", "권한", "audit", "access", "segregation"),
}


def _normalize(text: str) -> str:
    lowered = text.lower().strip()
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered


def detect_pain_point_categories(text: str) -> set[str]:
    """Return stable category tags detected from a free-text pain-point field."""
    normalized = _normalize(text)
    if not normalized:
        return set()

    categories: set[str] = set()
    for category, keywords in _CATEGORY_KEYWORDS.items():
        if any(keyword in normalized for keyword in keywords):
            categories.add(category)
    return categories
