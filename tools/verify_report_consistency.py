#!/usr/bin/env python3
"""Verify report numeric/date consistency for pre-confirm handoff."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from models.schemas import CustomerInput, ModuleInfo
from services.application.analysis_runner import AnalysisPolicy, run_analysis
from services.application.report_preflight import collect_preconfirm_issues


def _sample_inputs() -> list[CustomerInput]:
    return [
        CustomerInput(
            company_name="ConsistencyA",
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
        ),
        CustomerInput(
            company_name="ConsistencyB",
            industry="금융",
            erp_version="ECC 6.0",
            db_type="SQL Server",
            db_size_gb=1500.0,
            num_users=1200,
            num_custom_programs=900,
            custom_code_ratio=68.0,
            modules=[
                ModuleInfo(module_name="FI", customization_level="high"),
                ModuleInfo(module_name="CO", customization_level="high"),
                ModuleInfo(module_name="MM", customization_level="medium"),
                ModuleInfo(module_name="SD", customization_level="medium"),
            ],
            annual_it_budget_krw=45.0,
            pain_points="배치 실패, 운영비 증가",
            migration_timeline_months=14,
        ),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify report consistency.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    policy = AnalysisPolicy(analysis_mode="deterministic", rag_enabled=False, llm_enabled=False)
    findings: list[dict[str, object]] = []
    high_issue_exists = False
    analysis_date = date.today().isoformat()

    for inp in _sample_inputs():
        result = run_analysis(inp, policy=policy, lang="ko")
        preconfirm_issues, _metrics = collect_preconfirm_issues(
            result.output,
            analysis_date,
        )
        issues = [
            issue
            for issue in preconfirm_issues
            if issue.code.startswith("REPORT_")
            or issue.code == "UNMAPPED_DATE_CLAIM"
        ]
        if any(issue.severity == "HIGH" for issue in issues):
            high_issue_exists = True
        findings.append(
            {
                "company": inp.company_name,
                "issues": [asdict(issue) for issue in issues],
            }
        )

    if args.json:
        print(json.dumps(findings, ensure_ascii=False, indent=2))
    else:
        for row in findings:
            print(f"{row['company']}:")
            if not row["issues"]:
                print("  - PASS")
            for issue in row["issues"]:
                print(
                    f"  - [{issue['severity']}] {issue['code']}: {issue['message']}"
                )
    return 1 if high_issue_exists else 0


if __name__ == "__main__":
    raise SystemExit(main())
