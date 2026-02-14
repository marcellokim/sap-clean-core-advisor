"""Tests for PDF generator stability."""

from __future__ import annotations

import unittest

from models.schemas import AdvisorOutput, CustomerInput, ModuleInfo
from services.pdf_generator import generate_pdf


def _sample_input() -> CustomerInput:
    return CustomerInput(
        company_name="한국제조_매우긴회사명_" + ("A" * 80),
        industry="제조",
        erp_version="ECC 6.0",
        db_type="Oracle",
        db_size_gb=500.0,
        num_users=800,
        num_custom_programs=350,
        custom_code_ratio=45.0,
        modules=[
            ModuleInfo(module_name="FI", customization_level="medium"),
            ModuleInfo(module_name="CO", customization_level="medium"),
            ModuleInfo(module_name="MM", customization_level="medium"),
            ModuleInfo(module_name="SD", customization_level="medium"),
        ],
        annual_it_budget_krw=50.0,
        pain_points="결산 지연",
        migration_timeline_months=18,
    )


def _sample_output() -> AdvisorOutput:
    long_text = (
        "### 요약\n"
        + ("- 긴 텍스트 테스트 문장입니다. " * 40)
    )
    return AdvisorOutput(
        clean_core_score=42.6,
        score_breakdown={
            "custom_code": 32.5,
            "erp_version": 40.0,
            "database": 45.0,
            "module_complexity": 58.0,
        },
        current_annual_tco=1.06,
        projected_tco_after_migration=0.95,
        tco_savings_3yr=0.33,
        risk_level="Medium",
        risk_factors=[
            "커스텀 코드 비중 45.0% – 선별적 코드 정리 필요",
            "ECC 6.0 메인스트림 지원 종료 – 2027년까지 전환 권고",
            "현재 DB(Oracle)에서 SAP HANA로의 마이그레이션 필요 – 추가 비용 및 기간 발생",
        ],
        recommendations=[
            "사용하지 않는 Z-code 정리",
            "핵심 모듈 우선 전환",
        ],
        executive_summary=long_text,
        detailed_report=long_text,
        tech_debt_breakdown={
            "FI": 40.5,
            "SD": 37.8,
            "MM": 35.1,
            "CO": 32.4,
        },
        generation_mode="fallback",
        generation_provider="gemini",
        generation_error_code="rate_limit",
        analysis_id="test-analysis-id",
    )


class PdfGeneratorTests(unittest.TestCase):
    def test_generate_pdf_returns_non_empty_bytes_for_long_content(self) -> None:
        pdf_bytes = generate_pdf(_sample_output(), _sample_input())
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 1000)


if __name__ == "__main__":
    unittest.main()
