#!/usr/bin/env python3
"""Verify fast-lane prune hygiene constraints."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def _rg(pattern: str, targets: list[str]) -> str:
    cmd = ["rg", "-n", pattern, *targets]
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.strip()
    if result.returncode == 1:
        return ""
    raise RuntimeError(result.stderr.strip() or f"rg failed with code {result.returncode}")


def main() -> int:
    issues: list[dict[str, str]] = []

    industry_filter = ROOT / "services" / "industry_filter.py"
    if industry_filter.exists():
        issues.append(
            {
                "code": "PRUNE_BLOCKER_INDUSTRY_FILTER_EXISTS",
                "message": "services/industry_filter.py should remain removed.",
                "path": str(industry_filter.relative_to(ROOT)),
            }
        )

    policy_dir = ROOT / "services" / "infrastructure" / "policy"
    if policy_dir.exists():
        policy_sources = [p for p in policy_dir.rglob("*.py") if "__pycache__" not in p.parts]
        if policy_sources:
            issues.append(
                {
                    "code": "PRUNE_BLOCKER_POLICY_SOURCE_EXISTS",
                    "message": "services/infrastructure/policy should not contain active source files.",
                    "path": str(policy_dir.relative_to(ROOT)),
                }
            )

    deprecated_targets_output = _rg(
        r"\b(backtest|calibrate)\b",
        ["Makefile", "README.md", "docs", "scripts", "services", "ui", "app.py"],
    )
    if deprecated_targets_output:
        allowlist = [
            r"^scripts/verify_prune_hygiene\.py:",
            r"^README\.md:\d+:- `make verify-prune-hygiene`:",
        ]
        hit_lines = [line for line in deprecated_targets_output.splitlines() if line.strip()]
        offending = []
        for line in hit_lines:
            if any(re.search(pattern, line) for pattern in allowlist):
                continue
            offending.append(line)
        if offending:
            issues.append(
                {
                    "code": "PRUNE_BLOCKER_DEPRECATED_TARGET_REFERENCE",
                    "message": "Found deprecated backtest/calibrate references.",
                    "matches": "\n".join(offending[:20]),
                }
            )

    print(json.dumps(issues, ensure_ascii=False, indent=2))
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
