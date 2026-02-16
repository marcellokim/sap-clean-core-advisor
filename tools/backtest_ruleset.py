#!/usr/bin/env python3
"""Run ruleset backtest on calibration CSV files."""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.calibration_engine import evaluate_rows, split_train_holdout
from services.data_quality import validate_calibration_rows
from services.ruleset_loader import resolve_ruleset_profile

DEFAULT_DATA_DIR = PROJECT_ROOT / "calibration" / "data"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "calibration" / "reports"


def _load_rows(data_dir: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for csv_path in sorted(data_dir.glob("*.csv")):
        with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            rows.extend(row for row in reader)
    return rows


def _write_report(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Backtest ruleset performance.")
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR))
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    parser.add_argument("--industry", default="manufacturing")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    rows = _load_rows(data_dir)
    quality = validate_calibration_rows(rows)

    report_lines = [
        f"# Backtest Report ({date.today().isoformat()})",
        "",
        f"- Industry: {args.industry}",
        f"- Total rows: {len(rows)}",
        f"- Accepted rows: {quality.accepted_rows}",
    ]

    if quality.warnings:
        report_lines.append("")
        report_lines.append("## Quality Warnings")
        report_lines.extend(f"- {w}" for w in quality.warnings)

    if not quality.ok:
        report_lines.append("")
        report_lines.append("## Quality Errors")
        report_lines.extend(f"- {e}" for e in quality.errors)
        report_name = f"backtest_{date.today().strftime('%Y%m%d')}.md"
        report_path = Path(args.report_dir) / report_name
        _write_report(report_path, "\n".join(report_lines))
        print(f"Backtest skipped due to quality errors. Report: {report_path}")
        return 1

    resolution = resolve_ruleset_profile(args.industry)
    train_rows, holdout_rows = split_train_holdout(rows)
    train_metrics = evaluate_rows(train_rows, resolution.profile)
    holdout_metrics = evaluate_rows(holdout_rows, resolution.profile) if holdout_rows else train_metrics

    report_lines.extend(
        [
            "",
            "## Profile",
            f"- profile_id: {resolution.profile.profile_id}",
            f"- profile_source: {resolution.profile.profile_source}",
            f"- ruleset_version: {resolution.profile.ruleset_version}",
            "",
            "## Metrics",
            f"- Train TCO MAPE: {train_metrics.mape_tco:.4f}",
            f"- Train Risk Agreement: {train_metrics.risk_agreement:.4f}",
            f"- Holdout TCO MAPE: {holdout_metrics.mape_tco:.4f}",
            f"- Holdout Risk Agreement: {holdout_metrics.risk_agreement:.4f}",
        ]
    )

    report_name = f"backtest_{date.today().strftime('%Y%m%d')}.md"
    report_path = Path(args.report_dir) / report_name
    _write_report(report_path, "\n".join(report_lines))
    print(f"Backtest completed. Report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
