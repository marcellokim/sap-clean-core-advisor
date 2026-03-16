"""Infrastructure adapter for Chroma-based RAG retrieval."""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from services.infrastructure.compat_telemetry import mark_compat_usage

if TYPE_CHECKING:
    from langchain_chroma import Chroma
    from services.rag_pipeline import RAGContextBundle


@lru_cache(maxsize=1)
def _get_cached_vector_store_loader():
    import streamlit as st

    @st.cache_resource(show_spinner="Initializing Vector DB...")
    def _load_vector_store() -> "Chroma":
        from services.rag_pipeline import build_vector_store

        return build_vector_store()

    return _load_vector_store


def get_cached_vector_store() -> "Chroma":
    """Streamlit cached wrapper around ChromaDB initialization."""
    return _get_cached_vector_store_loader()()


def get_context_bundle_for_input(
    erp_version: str,
    modules: list[str],
    pain_points: str,
):
    """Lazy proxy preserved for existing patch targets/tests."""
    from services.rag_pipeline import get_context_bundle_for_input as impl

    return impl(
        erp_version=erp_version,
        modules=modules,
        pain_points=pain_points,
    )


class ChromaRAGProvider:
    """RAG provider adapter."""

    def __init__(self) -> None:
        """Initialize and cache the vector store on creation."""
        mark_compat_usage(
            contract="services.infrastructure.rag.chroma_provider.ChromaRAGProvider.__init__",
            replacement="services.rag_pipeline.build_vector_store/get_cached_vector_store",
        )
        get_cached_vector_store()

    def get_context_bundle(
        self,
        erp_version: str,
        modules: list[str],
        pain_points: str,
    ) -> "RAGContextBundle":
        mark_compat_usage(
            contract="services.infrastructure.rag.chroma_provider.ChromaRAGProvider.get_context_bundle",
            replacement="services.rag_pipeline.get_context_bundle_for_input",
        )

        return get_context_bundle_for_input(
            erp_version=erp_version,
            modules=modules,
            pain_points=pain_points,
        )
