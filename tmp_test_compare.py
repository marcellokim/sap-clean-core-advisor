import os
from dotenv import load_dotenv
from models.schemas import CustomerInput, ModuleInfo
from services.analysis_service import analyze_customer_input
from config.settings import settings
import json

load_dotenv()
settings.ANALYSIS_MODE = "hybrid"

input_data = CustomerInput(
    company_name="Samsung Electronics",
    industry="제조",
    erp_version="ECC 6.0",
    db_type="Oracle",
    db_size_gb=1024,
    num_users=1000,
    num_custom_programs=500,
    custom_code_ratio=45.0,
    modules=[
        ModuleInfo(module_name="FI", customization_level="high"),
        ModuleInfo(module_name="CO", customization_level="high"),
        ModuleInfo(module_name="MM", customization_level="medium")
    ],
    annual_it_budget_krw=100.0,
    pain_points="시스템 노후화로 인한 성능 저하 및 결산 지연. S/4HANA 도입 비용 부담.",
    migration_timeline_months=24
)

# Run Analysis with LLM
result = analyze_customer_input(input_data)

print("==== AI 🌟 EXPERT REPORT ====")
print(f"Mode: {result.output.generation_mode}")
print("--- Executive Summary ---")
print(result.output.executive_summary)
print("-------------------------")
print("--- Detailed Report ---")
print(result.output.detailed_report)
print("=============================")

# Run Analysis with Fallback
from services.application.analysis_runner import _build_fallback_reports
from services.cost_calculator import run_calculation
from services.domain.recommendation_engine import extract_recommendations

calc = run_calculation(input_data, "manufacturing")
recs = [t.text for t in extract_recommendations(calc, input_data)]
fallback = _build_fallback_reports(input_data, calc, recs)

print("\n\n==== FALLBACK 🧩 BASIC REPORT ====")
print("--- Executive Summary ---")
print(fallback.executive_summary)
print("-------------------------")
print("--- Detailed Report ---")
print(fallback.detailed_report)
print("==================================")
