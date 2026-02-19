"""Infrastructure adapter for FPDF rendering."""

from __future__ import annotations

from models.schemas import AdvisorOutput, CustomerInput
from services.pdf_generator import generate_pdf


class FPDFRenderer:
    """PDF renderer adapter."""

    def render(self, output: AdvisorOutput, customer: CustomerInput) -> bytes:
        return generate_pdf(output, customer)

