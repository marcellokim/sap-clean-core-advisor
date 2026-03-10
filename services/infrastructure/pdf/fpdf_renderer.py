"""Infrastructure adapter for FPDF rendering."""

from __future__ import annotations

from models.schemas import AdvisorOutput, CustomerInput
from services.infrastructure.compat_telemetry import mark_compat_usage
from services.pdf_generator import generate_pdf


class FPDFRenderer:
    """PDF renderer adapter."""

    def render(self, output: AdvisorOutput, customer: CustomerInput) -> bytes:
        mark_compat_usage(
            contract="services.infrastructure.pdf.fpdf_renderer.FPDFRenderer.render",
            replacement="services.pdf_generator.generate_pdf",
        )
        return generate_pdf(output, customer)
