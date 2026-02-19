"""Evidence ledger construction logic."""

from __future__ import annotations

import re

from models.schemas import EvidenceItem
from services.domain.recommendation_engine import RecommendationTrace
from services.rag_pipeline import RAGContextBundle
from services.reference_mapper import get_reference_source_ids


def _extract_source_text_map(rag_context: str) -> dict[str, str]:
    source_text_map: dict[str, str] = {}
    if not rag_context.strip():
        return source_text_map

    sections = [section.strip() for section in rag_context.split("\n\n---\n\n") if section.strip()]
    for section in sections:
        lines = section.splitlines()
        if not lines:
            continue
        match = re.search(r"\[출처:\s*([^\]]+)\]", lines[0])
        if not match:
            continue
        source = match.group(1).strip()
        body = "\n".join(lines[1:]).strip().lower()
        if source and body:
            source_text_map[source] = body
    return source_text_map


def _tokenize_claim(text: str) -> list[str]:
    raw_tokens = re.findall(r"[0-9A-Za-z가-힣]{2,}", text.lower())
    stopwords = {
        "현재",
        "전환",
        "권고",
        "기반",
        "계획",
        "검토",
        "포함",
        "하세요",
        "필요",
        "및",
        "에서",
        "으로",
        "대한",
    }
    tokens: list[str] = []
    seen: set[str] = set()
    for token in raw_tokens:
        if token in stopwords:
            continue
        if token not in seen:
            seen.add(token)
            tokens.append(token)
    return tokens


def _match_rag_sources_for_claim(
    claim_text: str,
    source_text_map: dict[str, str],
    fallback_sources: list[str],
) -> list[str]:
    if not source_text_map:
        return []

    claim_tokens = _tokenize_claim(claim_text)
    if not claim_tokens:
        return []

    scored: list[tuple[str, int]] = []
    for source, source_text in source_text_map.items():
        score = sum(1 for token in claim_tokens if token in source_text)
        if score > 0:
            scored.append((source, score))

    scored.sort(key=lambda item: item[1], reverse=True)
    matched = [source for source, _ in scored[:3]]
    if matched:
        return matched
    return list(dict.fromkeys(fallback_sources))[:3]


def grade_evidence(input_facts: list[str], rule_ids: list[str], rag_sources: list[str]) -> str:
    if input_facts and rule_ids:
        return "A"
    if rule_ids:
        return "B"
    if rag_sources:
        return "C"
    return "D"


def build_evidence_ledger(
    recommendation_traces: list[RecommendationTrace],
    generation_mode: str,
    rag_bundle: RAGContextBundle,
) -> list[EvidenceItem]:
    """Build claim-level evidence ledger with grade and sources."""
    source_text_map = _extract_source_text_map(rag_bundle.context)
    fallback_sources = list(dict.fromkeys(rag_bundle.sources))
    ledger: list[EvidenceItem] = []

    for idx, trace in enumerate(recommendation_traces, start=1):
        rag_sources = _match_rag_sources_for_claim(
            claim_text=trace.text,
            source_text_map=source_text_map,
            fallback_sources=fallback_sources,
        )
        evidence_grade = grade_evidence(trace.input_facts, trace.rule_ids, rag_sources)
        reference_source_ids = get_reference_source_ids(trace.rule_ids)
        ledger.append(
            EvidenceItem(
                claim_id=f"CLAIM_{idx:02d}",
                claim_text=trace.text,
                evidence_grade=evidence_grade,
                input_facts=trace.input_facts,
                rule_ids=trace.rule_ids,
                rag_sources=rag_sources,
                reference_source_ids=reference_source_ids,
                generation_mode=generation_mode,
            )
        )
    return ledger
