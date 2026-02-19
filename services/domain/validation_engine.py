"""Deterministic validation warnings for input consistency."""

from __future__ import annotations

from models.schemas import CustomerInput
from services.cost_calculator import CalculationResult


def build_validation_warnings(inp: CustomerInput, calc: CalculationResult) -> list[str]:
    """Return non-blocking warnings for suspicious inputs."""
    warnings: list[str] = []
    module_names = [m.module_name for m in inp.modules]

    if not module_names:
        warnings.append("사용 모듈이 비어 있습니다. 모듈 정보가 없으면 기술부채/전환우선순위 정확도가 낮아집니다.")
    else:
        seen: set[str] = set()
        duplicates: set[str] = set()
        for name in module_names:
            if name in seen:
                duplicates.add(name)
            seen.add(name)
        if duplicates:
            warnings.append(
                f"중복 모듈 입력이 감지되었습니다: {', '.join(sorted(duplicates))}. 중복 제거를 권장합니다."
            )

    if inp.custom_code_ratio >= 60 and inp.num_custom_programs < 50:
        warnings.append(
            "커스텀 코드 비중이 매우 높지만 커스텀 프로그램 수가 낮습니다. 산정 기준(라인수/오브젝트수)을 확인하세요."
        )
    if inp.custom_code_ratio <= 10 and inp.num_custom_programs > 300:
        warnings.append(
            "커스텀 코드 비중이 낮은데 커스텀 프로그램 수가 매우 높습니다. 분모 정의와 집계 대상을 확인하세요."
        )

    if inp.annual_it_budget_krw > 0:
        budget_ratio = calc.current_annual_tco / inp.annual_it_budget_krw
        if budget_ratio > 2.0:
            warnings.append(
                f"현재 TCO/예산 비율이 {budget_ratio:.2f}로 매우 높습니다. 예산값 단위(억원) 입력을 재확인하세요."
            )
        elif budget_ratio < 0.01:
            warnings.append(
                f"현재 TCO/예산 비율이 {budget_ratio:.2f}로 매우 낮습니다. 예산/사용자/커스텀 입력 누락 여부를 확인하세요."
            )

    if inp.migration_timeline_months <= 6 and inp.num_custom_programs >= 200:
        warnings.append(
            "전환 기간 대비 커스텀 프로그램 수가 많습니다. 단계적 전환 계획으로 기간 가정을 보수화하세요."
        )

    return warnings

