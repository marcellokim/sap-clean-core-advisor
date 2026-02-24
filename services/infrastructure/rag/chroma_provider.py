"""Infrastructure adapter for Chroma-based RAG retrieval."""

from __future__ import annotations

import streamlit as st
from langchain_chroma import Chroma

from services.rag_pipeline import RAGContextBundle, get_context_bundle_for_input, build_vector_store


@st.cache_resource(show_spinner="Initializing Vector DB...")
def get_cached_vector_store() -> Chroma:
    """Streamlit cached wrapper around ChromaDB initialization."""
    return build_vector_store()


class ChromaRAGProvider:
    """RAG provider adapter."""

    def __init__(self) -> None:
        """Initialize and cache the vector store on creation."""
        get_cached_vector_store()

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
