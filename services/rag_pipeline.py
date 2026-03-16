"""RAG 파이프라인: ChromaDB + multilingual-e5-small 임베딩.

SAP 공식 문서를 벡터 DB에 저장하고, 사용자 입력 컨텍스트를 기반으로
관련 문서 청크를 검색합니다.
할루시네이션 방지 및 SAP 공식 톤앤매너 유지를 위해 RAG를 구축합니다.
"""

from __future__ import annotations

import hashlib
import os
import warnings
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

from config.settings import settings

if TYPE_CHECKING:
    from langchain_chroma import Chroma
    from langchain_core.documents import Document

# ────────────────────────────────────────────────────────────────────
# 상수
# ────────────────────────────────────────────────────────────────────
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CHROMA_DIR = DATA_DIR / "chroma_db"
EMBEDDING_MODEL = "intfloat/multilingual-e5-small"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
COLLECTION_NAME = "sap_knowledge_base"
TOP_K = 5
DEFAULT_MAX_CONTEXT_CHARS = 6000

_CACHED_VECTOR_STORE: Any = None
_CACHED_DOCS_HASH: str | None = None


@dataclass(frozen=True)
class RAGContextBundle:
    """RAG 컨텍스트와 메타데이터."""

    context: str
    sources: list[str]
    chunk_count: int


def _get_max_context_chars() -> int:
    return max(1000, settings.RAG_MAX_CONTEXT_CHARS)


@lru_cache(maxsize=1)
def _get_embedding_function():
    """다국어 E5 임베딩 함수를 반환."""
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
    except ImportError:  # pragma: no cover - compatibility fallback
        warnings.filterwarnings(
            "ignore",
            message="The class `HuggingFaceEmbeddings` was deprecated in LangChain",
            category=Warning,
        )
        from langchain_community.embeddings import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def _document_cls():
    from langchain_core.documents import Document

    return Document


def _chroma_cls():
    from langchain_chroma import Chroma

    return Chroma


def _chunk_splitter():
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    return RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n## ", "\n### ", "\n\n", "\n", " "],
    )


def _load_markdown_docs() -> list["Document"]:
    """data/ 폴더의 Markdown 문서들을 LangChain Document로 로딩."""
    Document = _document_cls()
    docs: list[Document] = []
    for md_file in sorted(DATA_DIR.glob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        if not text.strip():
            continue
        docs.append(
            Document(
                page_content=text,
                metadata={"source": md_file.name},
            )
        )
    return docs


def _compute_docs_hash(docs: list["Document"]) -> str:
    """문서 내용의 해시를 계산하여 변경 감지에 활용."""
    hasher = hashlib.md5()
    for doc in docs:
        hasher.update(doc.page_content.encode("utf-8"))
    return hasher.hexdigest()


def _needs_rebuild(docs_hash: str) -> bool:
    """ChromaDB가 없거나 문서가 변경되었으면 True를 반환."""
    hash_file = CHROMA_DIR / ".docs_hash"
    if not CHROMA_DIR.exists() or not hash_file.exists():
        return True
    return hash_file.read_text().strip() != docs_hash


def build_vector_store(force: bool = False):
    """벡터 스토어를 구축하거나 기존 것을 로드.

    Args:
        force: True이면 기존 DB를 무시하고 재구축.

    Returns:
        Chroma 벡터 스토어 인스턴스.
    """
    global _CACHED_DOCS_HASH, _CACHED_VECTOR_STORE

    raw_docs = _load_markdown_docs()
    docs_hash = _compute_docs_hash(raw_docs)
    embeddings = _get_embedding_function()
    Chroma = _chroma_cls()

    if not force and _CACHED_VECTOR_STORE is not None and _CACHED_DOCS_HASH == docs_hash:
        return _CACHED_VECTOR_STORE

    if not force and not _needs_rebuild(docs_hash):
        # 기존 DB 로드
        _CACHED_VECTOR_STORE = Chroma(
            persist_directory=str(CHROMA_DIR),
            embedding_function=embeddings,
            collection_name=COLLECTION_NAME,
        )
        _CACHED_DOCS_HASH = docs_hash
        return _CACHED_VECTOR_STORE

    # 청크 분할
    splitter = _chunk_splitter()
    chunks = splitter.split_documents(raw_docs)

    # E5 모델은 passage: prefix가 필요
    for chunk in chunks:
        chunk.page_content = f"passage: {chunk.page_content}"

    # ChromaDB 생성/재구축
    os.makedirs(CHROMA_DIR, exist_ok=True)
    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(CHROMA_DIR),
        collection_name=COLLECTION_NAME,
    )

    # 해시 저장
    (CHROMA_DIR / ".docs_hash").write_text(docs_hash)

    _CACHED_VECTOR_STORE = vector_store
    _CACHED_DOCS_HASH = docs_hash

    return vector_store


def _search_with_store(vector_store, query: str, top_k: int) -> list["Document"]:
    """이미 로드된 벡터 스토어에서 쿼리를 검색."""
    prefixed_query = f"query: {query}"
    return vector_store.similarity_search(prefixed_query, k=top_k)


def search(query: str, top_k: int = TOP_K) -> list["Document"]:
    """쿼리와 관련된 SAP 문서 청크를 검색.

    E5 모델 규약에 따라 query에 'query: ' prefix를 추가합니다.

    Args:
        query: 검색 쿼리 문자열.
        top_k: 반환할 최대 결과 수.

    Returns:
        관련성 높은 Document 리스트.
    """
    vector_store = build_vector_store()
    return _search_with_store(vector_store, query, top_k)


def get_context_for_input(
    erp_version: str,
    modules: list[str],
    pain_points: str,
) -> str:
    """고객 입력 정보를 기반으로 RAG 컨텍스트를 생성.

    여러 관점(버전, 모듈, 고충)에서 검색하여 풍부한 컨텍스트를 제공합니다.
    """
    bundle = get_context_bundle_for_input(erp_version, modules, pain_points)
    return bundle.context


def get_context_bundle_for_input(
    erp_version: str,
    modules: list[str],
    pain_points: str,
) -> RAGContextBundle:
    """고객 입력 정보를 기반으로 RAG 컨텍스트 번들을 생성."""
    queries = [
        f"{erp_version}에서 S/4HANA 전환 시 고려사항",
        f"SAP {', '.join(modules)} 모듈의 Clean Core 전환 전략",
        f"SAP 마이그레이션 {pain_points}",
        "RISE with SAP TCO 절감 효과",
    ]

    vector_store = build_vector_store()
    all_chunks: list["Document"] = []
    seen_contents: set[str] = set()

    for q in queries:
        results = _search_with_store(vector_store, q, top_k=3)
        for doc in results:
            # 중복 제거
            content_key = doc.page_content[:100]
            if content_key not in seen_contents:
                seen_contents.add(content_key)
                all_chunks.append(doc)

    # passage: prefix 제거하여 깨끗한 컨텍스트 반환
    context_parts: list[str] = []
    sources: list[str] = []
    max_chars = _get_max_context_chars()

    for doc in all_chunks[:8]:  # 최대 8개 청크
        content = doc.page_content
        if content.startswith("passage: "):
            content = content[len("passage: "):]
        source = doc.metadata.get("source", "unknown")
        part = f"[출처: {source}]\n{content}"

        estimated_len = len("\n\n---\n\n".join(context_parts + [part]))
        if estimated_len > max_chars:
            break

        context_parts.append(part)
        sources.append(source)

    return RAGContextBundle(
        context="\n\n---\n\n".join(context_parts),
        sources=sources,
        chunk_count=len(context_parts),
    )
