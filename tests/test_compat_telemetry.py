"""Tests for safe-lane compatibility telemetry helpers and report script."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
import warnings
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from services.infrastructure import compat_telemetry


class CompatTelemetryTests(unittest.TestCase):
    def setUp(self) -> None:
        compat_telemetry._warned_contracts.clear()

    def test_mark_compat_usage_writes_jsonl_event_when_test_inclusion_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "compat_usage.jsonl"
            with patch.multiple(
                "config.settings.settings",
                COMPAT_TELEMETRY_ENABLE=True,
                COMPAT_TELEMETRY_LOG_PATH=str(log_path),
                COMPAT_TELEMETRY_INCLUDE_TESTS=True,
                COMPAT_DEPRECATION_WARN=False,
                COMPAT_DEPRECATION_REMOVE_AFTER="2026-06-30",
            ):
                compat_telemetry.mark_compat_usage(
                    contract="services.analysis_service.analyze_customer_input",
                    replacement="services.application.analysis_runner.run_analysis",
                )

            self.assertTrue(log_path.exists())
            lines = log_path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 1)
            payload = json.loads(lines[0])
            self.assertEqual(payload["event"], "compat_wrapper_used")
            self.assertEqual(
                payload["contract"],
                "services.analysis_service.analyze_customer_input",
            )
            self.assertEqual(payload["remove_after"], "2026-06-30")
            self.assertIn("timestamp_utc", payload)

    def test_mark_compat_usage_skips_file_write_during_tests_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "compat_usage.jsonl"
            with patch.multiple(
                "config.settings.settings",
                COMPAT_TELEMETRY_ENABLE=True,
                COMPAT_TELEMETRY_LOG_PATH=str(log_path),
                COMPAT_TELEMETRY_INCLUDE_TESTS=False,
                COMPAT_DEPRECATION_WARN=False,
            ):
                compat_telemetry.mark_compat_usage(
                    contract="services.infrastructure.pdf.fpdf_renderer.FPDFRenderer.render",
                    replacement="services.pdf_generator.generate_pdf",
                )

            self.assertFalse(log_path.exists())

    def test_mark_compat_usage_warns_once_per_contract(self) -> None:
        with patch.multiple(
            "config.settings.settings",
            COMPAT_TELEMETRY_ENABLE=False,
            COMPAT_DEPRECATION_WARN=True,
            COMPAT_DEPRECATION_REMOVE_AFTER="2026-06-30",
        ):
            with warnings.catch_warnings(record=True) as captured:
                warnings.simplefilter("always", DeprecationWarning)
                compat_telemetry.mark_compat_usage("contract.x", "replacement.a")
                compat_telemetry.mark_compat_usage("contract.x", "replacement.a")

        self.assertEqual(len(captured), 1)
        self.assertIn("2026-06-30", str(captured[0].message))


class CompatTelemetryReportScriptTests(unittest.TestCase):
    _ROOT = Path(__file__).resolve().parents[1]

    def test_report_counts_only_recent_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "compat_usage.jsonl"
            now = datetime.now(UTC)
            recent = {
                "event": "compat_wrapper_used",
                "contract": "services.analysis_service.analyze_customer_input",
                "replacement": "services.application.analysis_runner.run_analysis",
                "remove_after": "2026-06-30",
                "timestamp_utc": now.isoformat().replace("+00:00", "Z"),
            }
            old = {
                **recent,
                "contract": "services.infrastructure.pdf.fpdf_renderer.FPDFRenderer.render",
                "timestamp_utc": (now - timedelta(days=30)).isoformat().replace("+00:00", "Z"),
            }
            log_path.write_text(
                "\n".join(json.dumps(row, ensure_ascii=False) for row in [recent, old]) + "\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/compat_telemetry_report.py",
                    "--days",
                    "7",
                    "--json",
                    "--log-path",
                    str(log_path),
                ],
                capture_output=True,
                text=True,
                cwd=self._ROOT,
                check=False,
            )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["total_events_in_window"], 1)
        self.assertEqual(
            payload["contracts"],
            {"services.analysis_service.analyze_customer_input": 1},
        )
        self.assertFalse(payload["promotion_ready"])

    def test_report_require_log_fails_when_log_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "missing.jsonl"
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/compat_telemetry_report.py",
                    "--days",
                    "7",
                    "--json",
                    "--log-path",
                    str(log_path),
                    "--require-log",
                ],
                capture_output=True,
                text=True,
                cwd=self._ROOT,
                check=False,
            )
        self.assertEqual(result.returncode, 2, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["log_exists"])

    def test_report_fail_on_invalid_rows_fails_when_log_has_bad_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "compat_usage.jsonl"
            now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
            valid = {
                "event": "compat_wrapper_used",
                "contract": "services.analysis_service.analyze_customer_input",
                "replacement": "services.application.analysis_runner.run_analysis",
                "remove_after": "2026-06-30",
                "timestamp_utc": now,
            }
            malformed = {
                "event": "compat_wrapper_used",
                "contract": "services.infrastructure.pdf.fpdf_renderer.FPDFRenderer.render",
                "replacement": "services.pdf_generator.generate_pdf",
                "remove_after": "2026-06-30",
            }
            log_path.write_text(
                "\n".join([json.dumps(valid, ensure_ascii=False), "{bad-json", json.dumps(malformed)])
                + "\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/compat_telemetry_report.py",
                    "--days",
                    "7",
                    "--json",
                    "--log-path",
                    str(log_path),
                    "--fail-on-invalid-rows",
                ],
                capture_output=True,
                text=True,
                cwd=self._ROOT,
                check=False,
            )

        self.assertEqual(result.returncode, 1, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["invalid_rows"], 2)

    def test_report_fail_on_invalid_rows_passes_when_log_rows_are_valid(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "compat_usage.jsonl"
            row = {
                "event": "compat_wrapper_used",
                "contract": "services.analysis_service.analyze_customer_input",
                "replacement": "services.application.analysis_runner.run_analysis",
                "remove_after": "2026-06-30",
                "timestamp_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            }
            log_path.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/compat_telemetry_report.py",
                    "--days",
                    "7",
                    "--json",
                    "--log-path",
                    str(log_path),
                    "--fail-on-invalid-rows",
                ],
                capture_output=True,
                text=True,
                cwd=self._ROOT,
                check=False,
            )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["invalid_rows"], 0)
        self.assertEqual(payload["total_events_in_window"], 1)


if __name__ == "__main__":
    unittest.main()
