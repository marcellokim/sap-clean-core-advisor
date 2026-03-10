"""Report pre-confirm validation and PDF rendering gate helpers."""

from __future__ import annotations

import logging
from typing import Literal

from models.schemas import AdvisorOutput, CustomerInput
from services.domain.claim_extractor import extract_report_claims
from services.domain.citation_validator import CitationCoverage, validate_citation_coverage
from services.domain.date_claim_validator import validate_date_claims
from services.domain.report_consistency import validate_report_consistency
from services.domain.verification_types import ValidationIssue
from services.error_codes import (
    ERR_PDF_FONT,
    ERR_PDF_LAYOUT_OVERFLOW,
    ERR_PDF_UNKNOWN,
    ERR_REPORT_VALIDATION,
)
from services.infrastructure.pdf.fpdf_renderer import FPDFRenderer
from config.settings import settings

logger = logging.getLogger(__name__)

PDFStatus = Literal["ok", "failed"]


def _classify_pdf_error(exc: Exception) -> str:
    msg = str(exc).lower()
    if "not enough horizontal space" in msg:
        return ERR_PDF_LAYOUT_OVERFLOW
    if "font" in msg:
        return ERR_PDF_FONT
    return ERR_PDF_UNKNOWN


def run_preconfirm_validation(
    output: AdvisorOutput,
    analysis_date: str,
    validation_warnings: list[str],
) -> tuple[AdvisorOutput, list[ValidationIssue], CitationCoverage | None]:
    """Run pre-confirm validation suite and append warnings to output."""
    if not settings.REPORT_PREFLIGHT_ENABLE:
        return output, [], None

    updated_warnings = list(validation_warnings)
    report_claims = extract_report_claims(
        output.executive_summary,
        output.detailed_report,
    )
    citation_issues, citation_metrics = validate_citation_coverage(
        output.evidence_ledger,
        report_claims,
        strict_reference_ids=True,
    )
    consistency_issues = validate_report_consistency(output)
    date_issues = validate_date_claims(
        output.executive_summary,
        output.detailed_report,
        analysis_date=analysis_date,
    )
    preconfirm_issues = citation_issues + consistency_issues + date_issues

    for issue in preconfirm_issues:
        updated_warnings.append(
            f"REPORT_PRECONFIRM_{issue.severity}_{issue.code}: {issue.message}"
        )
    if citation_metrics and citation_metrics.coverage_ratio < 1.0:
        updated_warnings.append(
            "REPORT_PRECONFIRM_CITATION_COVERAGE: "
            f"{citation_metrics.with_reference_source_ids}/{citation_metrics.total_claims}"
        )

    return (
        output.model_copy(update={"validation_warnings": updated_warnings}),
        preconfirm_issues,
        citation_metrics,
    )


def render_pdf_output(
    output: AdvisorOutput,
    customer_input: CustomerInput,
    preconfirm_issues: list[ValidationIssue],
) -> tuple[bytes | None, str | None, str | None, PDFStatus]:
    """Render PDF unless blocked by pre-confirm HIGH issues."""
    should_block_pdf = (
        settings.REPORT_PREFLIGHT_ENABLE
        and settings.REPORT_PREFLIGHT_BLOCK_ON_HIGH
        and any(issue.severity == "HIGH" for issue in preconfirm_issues)
    )

    if should_block_pdf:
        high_issue_codes = [
            issue.code
            for issue in preconfirm_issues
            if issue.severity == "HIGH"
        ]
        pdf_error_message = (
            "Pre-confirm validation failed: "
            + ", ".join(high_issue_codes[:10])
        )
        logger.warning(
            "PDF generation blocked by pre-confirm validation: %s",
            pdf_error_message,
        )
        return None, ERR_REPORT_VALIDATION, pdf_error_message, "failed"

    try:
        renderer = FPDFRenderer()
        return renderer.render(output, customer_input), None, None, "ok"
    except Exception as exc:
        pdf_error_code = _classify_pdf_error(exc)
        pdf_error_message = str(exc).strip() or None
        logger.warning("PDF generation failed: [%s] %s", pdf_error_code, exc)
        return None, pdf_error_code, pdf_error_message, "failed"

