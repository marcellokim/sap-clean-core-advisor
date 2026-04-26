"""Rule ID to reference source mapping for evidence ledger."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from services.config_utils import load_json_yaml

DEFAULT_RULE_REFERENCE_PATH = (
    Path(__file__).resolve().parent.parent / "config" / "rule_reference_map.yaml"
)

RAG_SOURCE_REFERENCE_MAP: dict[str, list[str]] = {
    "btp_use_cases.md": ["SRC_SAP_CLEAN_CORE"],
    "clean_core_strategy.md": ["SRC_SAP_CLEAN_CORE"],
    "migration_best_practices.md": [
        "SRC_SAP_READINESS_CHECK",
        "SRC_SAP_CUSTOM_CODE_MIGRATION",
    ],
    "rise_with_sap.md": [
        "SRC_SAP_CLEAN_CORE",
        "SRC_ASUG_S4_ADOPTION",
    ],
    "sap_modules_overview.md": ["SRC_SAP_READINESS_CHECK"],
    "tco_benchmarks.md": [
        "SRC_ASUG_S4_ADOPTION",
        "SRC_SAPINSIDER_MIGRATION_2025",
    ],
}


@lru_cache(maxsize=1)
def get_rule_reference_map() -> dict[str, list[str]]:
    payload = load_json_yaml(DEFAULT_RULE_REFERENCE_PATH)
    raw_map = payload.get("rule_sources", {})
    if not isinstance(raw_map, dict):
        return {}

    normalized: dict[str, list[str]] = {}
    for key, values in raw_map.items():
        if not isinstance(key, str):
            continue
        if not isinstance(values, list):
            continue
        normalized[key] = [v for v in values if isinstance(v, str)]
    return normalized


def get_reference_source_ids(rule_ids: list[str]) -> list[str]:
    """Return unique source IDs for given rule IDs."""
    reference_map = get_rule_reference_map()
    source_ids: list[str] = []
    for rule_id in rule_ids:
        source_ids.extend(reference_map.get(rule_id, []))
    # order-preserving unique
    return list(dict.fromkeys(source_ids))


def get_rag_reference_source_ids(rag_sources: list[str]) -> list[str]:
    """Return source catalog IDs for local RAG markdown sources."""
    source_ids: list[str] = []
    for rag_source in rag_sources:
        source_ids.extend(RAG_SOURCE_REFERENCE_MAP.get(Path(rag_source).name, []))
    return list(dict.fromkeys(source_ids))
