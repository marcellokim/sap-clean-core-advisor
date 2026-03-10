#!/usr/bin/env python3
"""Run final release-readiness gates and persist a machine-readable report."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def _tail(text: str, lines: int = 20) -> str:
    rows = text.strip().splitlines()
    if not rows:
        return ""
    return "\n".join(rows[-lines:])


def _run(cmd: list[str]) -> dict[str, object]:
    started = time.perf_counter()
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
    duration_ms = int((time.perf_counter() - started) * 1000)
    return {
        "command": " ".join(cmd),
        "returncode": proc.returncode,
        "duration_ms": duration_ms,
        "stdout_tail": _tail(proc.stdout),
        "stderr_tail": _tail(proc.stderr),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qa-runs", type=int, default=3)
    parser.add_argument(
        "--output",
        default="artifacts/qa/release_readiness.json",
        help="JSON report output path (repo-relative or absolute).",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    qa_runs = max(1, args.qa_runs)
    commands: list[list[str]] = []
    for _ in range(qa_runs):
        commands.append(["make", "qa-report"])
    commands.extend(
        [
            ["make", "test-compat"],
            ["make", "check-import-cycles"],
            ["make", "verify-safe-lane-promotion"],
        ]
    )

    results: list[dict[str, object]] = []
    all_ok = True
    for cmd in commands:
        result = _run(cmd)
        results.append(result)
        if int(result["returncode"]) != 0:
            all_ok = False
            break

    report = {
        "as_of_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "qa_runs_required": qa_runs,
        "commands_executed": len(results),
        "ok": all_ok,
        "results": results,
    }

    output = Path(args.output)
    if not output.is_absolute():
        output = ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"[release-readiness] ok={all_ok} report={output}")

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
