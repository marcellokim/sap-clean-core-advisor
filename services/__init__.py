"""SAP Clean Core Advisor services package.

This package intentionally uses lazy exports to avoid heavy import side effects
when lightweight modules (e.g. ``services.config_utils``) are imported.
"""

from __future__ import annotations

from importlib import import_module

_EXPORT_MAP: dict[str, tuple[str, str]] = {
    "AnalysisResult": ("services.analysis_service", "AnalysisResult"),
    "AnalysisPolicy": ("services.analysis_service", "AnalysisPolicy"),
    "analyze_customer_input": ("services.analysis_service", "analyze_customer_input"),
    "run_analysis": ("services.analysis_service", "run_analysis"),
    "run_calculation": ("services.cost_calculator", "run_calculation"),
    "IndustryResolution": ("services.industry_mapper", "IndustryResolution"),
    "resolve_industry_profile": ("services.industry_mapper", "resolve_industry_profile"),
    "GeminiLLMProvider": ("services.infrastructure.llm.gemini_provider", "GeminiLLMProvider"),
    "LLMProviderError": ("services.llm_provider", "LLMProviderError"),
    "LLMUsage": ("services.llm_provider", "LLMUsage"),
    "ReportPayload": ("services.llm_provider", "ReportPayload"),
    "ReportSections": ("services.llm_provider", "ReportSections"),
    "generate_pdf": ("services.pdf_generator", "generate_pdf"),
    "RAGContextBundle": ("services.rag_pipeline", "RAGContextBundle"),
    "build_vector_store": ("services.rag_pipeline", "build_vector_store"),
    "search": ("services.rag_pipeline", "search"),
    "RulesetProfile": ("services.ruleset_loader", "RulesetProfile"),
    "RulesetResolution": ("services.ruleset_loader", "RulesetResolution"),
    "resolve_ruleset_profile": ("services.ruleset_loader", "resolve_ruleset_profile"),
}

__all__ = sorted(_EXPORT_MAP.keys())


def __getattr__(name: str):
    target = _EXPORT_MAP.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = target
    module = import_module(module_name)
    return getattr(module, attr_name)

