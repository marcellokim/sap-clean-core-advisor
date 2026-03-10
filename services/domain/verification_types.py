"""Shared types for pre-confirmation validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


ValidationSeverity = Literal["HIGH", "MEDIUM", "LOW"]


@dataclass(frozen=True)
class ValidationIssue:
    """Validation issue used by report/source pre-confirm checks."""

    severity: ValidationSeverity
    code: str
    message: str
