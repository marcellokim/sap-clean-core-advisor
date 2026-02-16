"""PDF EA Cookbook 생성기.

AdvisorOutput을 받아 'Preliminary EA Cookbook' 형태의 PDF를 생성합니다.
한글 폰트(Noto Sans KR)를 반드시 등록해야 합니다.
"""

from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path

from fpdf import FPDF

from models.schemas import AdvisorOutput, CustomerInput

# ────────────────────────────────────────────────────────────────────
# 경로 및 색상 상수
# ────────────────────────────────────────────────────────────────────
FONTS_DIR = Path(__file__).resolve().parent.parent / "data" / "fonts"
FONT_FILE = FONTS_DIR / "NotoSansKR-Regular.ttf"

# SAP 브랜드 색상 (RGB)
SAP_BLUE = (0, 112, 242)
SAP_DARK = (27, 37, 89)
SAP_GREEN = (54, 164, 29)
SAP_ORANGE = (231, 101, 0)
SAP_RED = (187, 0, 0)
WHITE = (255, 255, 255)
LIGHT_GRAY = (245, 245, 245)
DARK_GRAY = (80, 80, 80)


class EACookbookPDF(FPDF):
    """EA Cookbook PDF 생성 클래스."""

    def __init__(self, company_name: str) -> None:
        super().__init__()
        self.company_name = company_name
        self._register_fonts()

    def _register_fonts(self) -> None:
        """한글 폰트를 등록."""
        font_path = str(FONT_FILE)
        self.add_font("NotoSansKR", "", font_path)
        # 변수 폰트이므로 동일 파일을 Bold로도 등록
        self.add_font("NotoSansKR", "B", font_path)

    def header(self) -> None:
        """페이지 헤더."""
        if self.page_no() == 1:
            return  # 표지에는 헤더 없음
        self.set_font("NotoSansKR", "", 8)
        self.set_text_color(*DARK_GRAY)
        page_width = self.w - self.l_margin - self.r_margin
        self.cell(
            page_width * 0.8,
            8,
            f"RISE with SAP: Clean Core Assessment – {self.company_name}",
            align="L",
            new_x="RIGHT",
            new_y="TOP",
        )
        self.cell(
            page_width * 0.2,
            8,
            f"Page {self.page_no()}",
            align="R",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        self.set_draw_color(*SAP_BLUE)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(4)

    def footer(self) -> None:
        """페이지 푸터."""
        if self.page_no() == 1:
            return
        self.set_y(-15)
        self.set_font("NotoSansKR", "", 7)
        self.set_text_color(*DARK_GRAY)
        self.cell(
            0, 10,
            "Confidential – Preliminary EA Cookbook (Auto-generated)",
            align="C",
        )

    def _add_cover_page(self, customer: CustomerInput) -> None:
        """표지 페이지."""
        self.add_page()
        self.ln(50)

        # 타이틀
        self.set_font("NotoSansKR", "B", 26)
        self.set_text_color(*SAP_DARK)
        self.cell(0, 15, "RISE with SAP", align="C", new_x="LMARGIN", new_y="NEXT")

        self.set_font("NotoSansKR", "B", 18)
        self.set_text_color(*SAP_BLUE)
        self.cell(0, 12, "Clean Core Assessment & TCO Simulator", align="C", new_x="LMARGIN", new_y="NEXT")

        self.ln(8)

        # 구분선
        self.set_draw_color(*SAP_BLUE)
        self.set_line_width(0.8)
        self.line(60, self.get_y(), 150, self.get_y())
        self.ln(10)

        # 부제목
        self.set_font("NotoSansKR", "", 14)
        self.set_text_color(*SAP_DARK)
        self.cell(0, 10, "Preliminary EA Cookbook", align="C", new_x="LMARGIN", new_y="NEXT")

        self.ln(20)

        # 고객사 정보 박스
        self.set_fill_color(*LIGHT_GRAY)
        self.set_font("NotoSansKR", "", 11)
        self.set_text_color(*DARK_GRAY)

        info_lines = [
            f"고객사: {customer.company_name}",
            f"업종: {customer.industry}",
            f"ERP 버전: {customer.erp_version} / DB: {customer.db_type}",
            f"사용자 수: {customer.num_users:,}명 / 커스텀 비중: {customer.custom_code_ratio}%",
        ]
        box_y = self.get_y()
        self.rect(40, box_y, 130, len(info_lines) * 10 + 10, style="F")
        self.ln(5)
        for line in info_lines:
            self.cell(0, 10, line, align="C", new_x="LMARGIN", new_y="NEXT")

        self.ln(30)
        self.set_font("NotoSansKR", "", 9)
        self.set_text_color(*DARK_GRAY)
        self.cell(0, 8, "본 문서는 AI 기반 사전 분석 자료이며, 정밀 진단을 대체하지 않습니다.", align="C")

    def _add_section_title(self, title: str) -> None:
        """섹션 제목."""
        self.ln(6)
        self.set_font("NotoSansKR", "B", 14)
        self.set_text_color(*SAP_DARK)
        self.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*SAP_BLUE)
        self.set_line_width(0.5)
        self.line(10, self.get_y(), 80, self.get_y())
        self.ln(4)

    def _add_subsection_title(self, title: str) -> None:
        """하위 섹션 제목."""
        self.ln(3)
        self.set_font("NotoSansKR", "B", 11)
        self.set_text_color(*SAP_BLUE)
        self.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def _add_body_text(self, text: str) -> None:
        """본문 텍스트 (Markdown 간이 파싱)."""
        self.set_font("NotoSansKR", "", 10)
        self.set_text_color(*DARK_GRAY)

        for line in text.split("\n"):
            stripped = line.strip()
            if not stripped:
                self.set_x(self.l_margin)
                self.ln(3)
                continue

            self.set_x(self.l_margin)

            # Markdown 헤더 처리
            if stripped.startswith("### "):
                self._add_subsection_title(stripped[4:])
            elif stripped.startswith("## "):
                self._add_section_title(stripped[3:])
            elif stripped.startswith("# "):
                self._add_section_title(stripped[2:])
            elif stripped.startswith("- ") or stripped.startswith("* "):
                self.set_font("NotoSansKR", "", 10)
                self.set_text_color(*DARK_GRAY)
                # 볼드 마크다운 간이 제거
                clean = re.sub(r"\*\*(.*?)\*\*", r"\1", stripped[2:])
                self.set_x(self.l_margin + 4)
                self.multi_cell(0, 6, f"• {clean}")
            elif stripped.startswith(tuple(f"{i}." for i in range(1, 20))):
                self.set_font("NotoSansKR", "", 10)
                self.set_text_color(*DARK_GRAY)
                clean = re.sub(r"\*\*(.*?)\*\*", r"\1", stripped)
                self.set_x(self.l_margin + 2)
                self.multi_cell(0, 6, clean)
            else:
                self.set_font("NotoSansKR", "", 10)
                self.set_text_color(*DARK_GRAY)
                clean = re.sub(r"\*\*(.*?)\*\*", r"\1", stripped)
                self.set_x(self.l_margin)
                self.multi_cell(0, 6, clean)

    def _add_kpi_box(self, output: AdvisorOutput) -> None:
        """핵심 KPI 요약 박스."""
        self.add_page()
        self._add_section_title("핵심 지표 요약")
        self.ln(2)

        # KPI 테이블
        self.set_font("NotoSansKR", "B", 10)
        col_w = 47.5
        row_h = 22

        kpis = [
            ("Clean Core Score", f"{output.clean_core_score:.1f} / 100"),
            ("현재 연간 TCO", f"{output.current_annual_tco:.1f} 억원"),
            ("전환 후 TCO", f"{output.projected_tco_after_migration:.1f} 억원"),
            ("3년 절감액", f"{output.tco_savings_3yr:.1f} 억원"),
        ]

        for label, value in kpis:
            self.set_fill_color(*SAP_BLUE)
            self.set_text_color(*WHITE)
            self.set_font("NotoSansKR", "B", 9)
            self.cell(col_w, row_h // 2, label, border=1, fill=True, align="C")

        self.ln()

        colors = [SAP_DARK, SAP_RED, SAP_BLUE, SAP_GREEN]
        for (_, value), color in zip(kpis, colors):
            self.set_fill_color(*LIGHT_GRAY)
            self.set_text_color(*color)
            self.set_font("NotoSansKR", "B", 12)
            self.cell(col_w, row_h // 2 + 4, value, border=1, fill=True, align="C")

        self.ln()

        # 리스크 수준
        self.ln(6)
        risk_color = {
            "High": SAP_RED, "Medium": SAP_ORANGE, "Low": SAP_GREEN,
        }.get(output.risk_level, SAP_ORANGE)
        self.set_font("NotoSansKR", "B", 11)
        self.set_text_color(*risk_color)
        self.cell(0, 10, f"전체 리스크 수준: {output.risk_level}", new_x="LMARGIN", new_y="NEXT")

    def _add_risk_factors(self, output: AdvisorOutput) -> None:
        """리스크 요인 섹션."""
        self._add_section_title("리스크 요인")
        self.set_font("NotoSansKR", "", 10)
        self.set_text_color(*DARK_GRAY)
        for rf in output.risk_factors:
            self.set_x(self.l_margin + 2)
            self.multi_cell(0, 6, f"⚠ {rf}")
            self.ln(2)

    def _add_recommendations(self, output: AdvisorOutput) -> None:
        """권고사항 섹션."""
        self._add_section_title("핵심 권고사항")
        self.set_font("NotoSansKR", "", 10)
        self.set_text_color(*DARK_GRAY)
        for idx, rec in enumerate(output.recommendations, 1):
            self.set_x(self.l_margin + 2)
            self.multi_cell(0, 6, f"{idx}. {rec}")
            self.ln(2)

    def _add_tech_debt_table(self, tech_debt: dict[str, float]) -> None:
        """기술 부채 테이블."""
        self._add_section_title("모듈별 기술 부채 분석")

        self.set_font("NotoSansKR", "B", 10)
        self.set_fill_color(*SAP_BLUE)
        self.set_text_color(*WHITE)
        self.cell(40, 8, "모듈", border=1, fill=True, align="C")
        self.cell(50, 8, "기술 부채 점수", border=1, fill=True, align="C")
        self.cell(50, 8, "심각도", border=1, fill=True, align="C")
        self.ln()

        sorted_items = sorted(tech_debt.items(), key=lambda x: x[1], reverse=True)
        for mod, score in sorted_items:
            if score >= 50:
                level, color = "높음", SAP_RED
            elif score >= 25:
                level, color = "보통", SAP_ORANGE
            else:
                level, color = "낮음", SAP_GREEN

            self.set_font("NotoSansKR", "", 10)
            self.set_text_color(*DARK_GRAY)
            self.set_fill_color(*LIGHT_GRAY)
            self.cell(40, 8, mod, border=1, fill=True, align="C")
            self.cell(50, 8, f"{score:.1f}", border=1, fill=True, align="C")
            self.set_text_color(*color)
            self.cell(50, 8, level, border=1, fill=True, align="C")
            self.ln()


def generate_pdf(
    output: AdvisorOutput,
    customer: CustomerInput,
) -> bytes:
    """AdvisorOutput과 CustomerInput을 받아 EA Cookbook PDF를 생성.

    Returns:
        PDF 파일의 바이트 데이터.
    """
    pdf = EACookbookPDF(customer.company_name)

    # 1. 표지
    pdf._add_cover_page(customer)

    # 2. 핵심 KPI
    pdf._add_kpi_box(output)

    # 3. 기술 부채 테이블
    pdf.ln(8)
    pdf._add_tech_debt_table(output.tech_debt_breakdown)

    # 4. 리스크 요인
    pdf.ln(4)
    pdf._add_risk_factors(output)

    # 5. 권고사항
    pdf.ln(4)
    pdf._add_recommendations(output)

    # 6. Executive Summary
    pdf.add_page()
    pdf._add_section_title("Executive Summary")
    pdf._add_body_text(output.executive_summary)

    # 7. 상세 리포트
    pdf.add_page()
    pdf._add_section_title("상세 분석 리포트")
    pdf._add_body_text(output.detailed_report)

    # BytesIO로 출력
    buffer = BytesIO()
    pdf.output(buffer)
    return buffer.getvalue()
