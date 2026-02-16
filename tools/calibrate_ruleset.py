#!/usr/bin/env python3
"""Calibrate ruleset from real project CSV data."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.calibration_engine import calibrate_ruleset
from services.ruleset_loader import resolve_ruleset_profile

DEFAULT_DATA_DIR = PROJECT_ROOT / "calibration" / "data"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "calibration" / "reports"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "config" / "rulesets" / "generated"


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
    parser = argparse.ArgumentParser(description="Calibrate industry ruleset.")
    parser.add_argument("--industry", required=True)
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR))
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    rows = _load_rows(Path(args.data_dir))
    resolution = resolve_ruleset_profile(args.industry)
    result = calibrate_ruleset(rows, resolution.profile)

    report_lines = [
        f"# Calibration Report ({date.today().isoformat()})",
        "",
        f"- Industry input: {args.industry}",
        f"- Base profile: {resolution.profile.profile_id}",
        f"- Base source: {resolution.profile.profile_source}",
        f"- Calibration success: {result.ok}",
        f"- Loss: {result.loss:.6f}",
        "",
        "## Train Metrics",
        f"- TCO MAPE: {result.train_metrics.mape_tco:.4f}",
        f"- Risk agreement: {result.train_metrics.risk_agreement:.4f}",
        "",
        "## Holdout Metrics",
        f"- TCO MAPE: {result.holdout_metrics.mape_tco:.4f}",
        f"- Risk agreement: {result.holdout_metrics.risk_agreement:.4f}",
    ]
    if result.warnings:
        report_lines.extend(["", "## Warnings", *[f"- {w}" for w in result.warnings]])
    if result.errors:
        report_lines.extend(["", "## Errors", *[f"- {e}" for e in result.errors]])

    report_path = Path(args.report_dir) / f"calibration_{date.today().strftime('%Y%m%d')}.md"
    _write_report(report_path, "\n".join(report_lines))

    if not result.ok:
        print(f"Calibration failed quality gate. Report: {report_path}")
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{resolution.profile.profile_id}.yaml"
    output_path.write_text(
        json.dumps(result.tuned_ruleset, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Calibration succeeded. Generated ruleset: {output_path}")
    print(f"Report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
