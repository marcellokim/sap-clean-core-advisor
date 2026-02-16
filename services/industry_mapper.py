"""Industry normalization and canonical profile mapping."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from services.config_utils import load_json_yaml

DEFAULT_ALIAS_PATH = Path(__file__).resolve().parent.parent / "config" / "industry_aliases.yaml"


@dataclass(frozen=True)
class IndustryResolution:
    """Resolved industry key with mapping metadata."""

    raw_input: str
    normalized_input: str
    profile_key: str
    matched: bool


def _normalize_text(value: str) -> str:
    cleaned = value.strip().lower()
    cleaned = re.sub(r"[^0-9a-zA-Z가-힣]+", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


@lru_cache(maxsize=1)
def _load_alias_map() -> dict[str, list[str]]:
    payload = load_json_yaml(DEFAULT_ALIAS_PATH)
    raw_aliases = payload.get("aliases", {})
    if not isinstance(raw_aliases, dict):
        return {}

    alias_map: dict[str, list[str]] = {}
    for key, aliases in raw_aliases.items():
        if not isinstance(key, str) or not isinstance(aliases, list):
            continue
        normalized_aliases = [_normalize_text(a) for a in aliases if isinstance(a, str)]
        normalized_aliases.append(_normalize_text(key))
        alias_map[key] = sorted(set(a for a in normalized_aliases if a))
    return alias_map


def resolve_industry_profile(industry: str) -> IndustryResolution:
    """Resolve user-provided industry text to canonical profile key."""
    normalized_input = _normalize_text(industry)
    alias_map = _load_alias_map()

    if not normalized_input:
        return IndustryResolution(industry, normalized_input, "base", False)

    for canonical, aliases in alias_map.items():
        if normalized_input == _normalize_text(canonical) or normalized_input in aliases:
            return IndustryResolution(industry, normalized_input, canonical, True)

    return IndustryResolution(industry, normalized_input, "base", False)
