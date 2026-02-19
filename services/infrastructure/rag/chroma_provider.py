"""Infrastructure adapter for Chroma-based RAG retrieval."""

from __future__ import annotations

from services.rag_pipeline import RAGContextBundle, get_context_bundle_for_input


class ChromaRAGProvider:
    """RAG provider adapter."""

    def get_context_bundle(
        self,
        erp_version: str,
        modules: list[str],
        pain_points: str,
    ) -> RAGContextBundle:
        return get_context_bundle_for_input(
            erp_version=erp_version,
            modules=modules,
            pain_points=pain_points,
        )

