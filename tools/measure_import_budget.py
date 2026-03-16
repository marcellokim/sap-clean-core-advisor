#!/usr/bin/env python3
"""Capture repeated subprocess import timings and module snapshots for import-budget reviews."""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "artifacts" / "perf" / "import_budget.json"
DEFAULT_MODULES_OUTPUT_PATH = PROJECT_ROOT / "artifacts" / "perf" / "import_modules.json"
DEFAULT_TARGETS = ("app", "analysis_runner")
DEFAULT_HEAVY_PREFIXES = ("chromadb", "langchain", "sentence_transformers")
TARGET_ALIASES = {
    "app": "app",
    "analysis_runner": "services.application.analysis_runner",
}


def _resolve_target(name: str) -> tuple[str, str]:
    normalized = name.strip()
    if not normalized:
        raise ValueError("target name cannot be empty")
    return normalized, TARGET_ALIASES.get(normalized, normalized)


def _resolve_output_path(raw: str) -> Path:
    candidate = Path(raw)
    if candidate.is_absolute():
        return candidate
    return PROJECT_ROOT / candidate


def _tail(text: str, lines: int = 20) -> str:
    rows = [line for line in text.strip().splitlines() if line.strip()]
    if not rows:
        return ""
    return "\n".join(rows[-lines:])


def _last_non_empty_line(text: str) -> str:
    for line in reversed(text.splitlines()):
        if line.strip():
            return line.strip()
    return ""


def _run_subprocess(code: str, timeout_sec: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout_sec,
    )


def _measure_import(module_name: str, timeout_sec: int) -> dict[str, Any]:
    code = (
        "import importlib\n"
        f"importlib.import_module({module_name!r})\n"
    )
    started = time.perf_counter()
    try:
        proc = _run_subprocess(code, timeout_sec=timeout_sec)
        duration_ms = round((time.perf_counter() - started) * 1000, 3)
        return {
            "returncode": proc.returncode,
            "duration_ms": duration_ms,
            "stdout_tail": _tail(proc.stdout),
            "stderr_tail": _tail(proc.stderr),
        }
    except subprocess.TimeoutExpired as exc:
        duration_ms = round((time.perf_counter() - started) * 1000, 3)
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        return {
            "returncode": 124,
            "duration_ms": duration_ms,
            "stdout_tail": _tail(stdout),
            "stderr_tail": _tail(f"{stderr}\n[timeout] import exceeded {timeout_sec}s"),
        }


def _capture_modules(module_name: str, timeout_sec: int) -> dict[str, Any]:
    code = (
        "import importlib\n"
        "import json\n"
        "import sys\n"
        f"importlib.import_module({module_name!r})\n"
        "print(json.dumps(sorted(sys.modules)))\n"
    )
    try:
        proc = _run_subprocess(code, timeout_sec=timeout_sec)
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        return {
            "returncode": 124,
            "stdout_tail": _tail(stdout),
            "stderr_tail": _tail(f"{stderr}\n[timeout] module snapshot exceeded {timeout_sec}s"),
            "modules": [],
        }

    if proc.returncode != 0:
        return {
            "returncode": proc.returncode,
            "stdout_tail": _tail(proc.stdout),
            "stderr_tail": _tail(proc.stderr),
            "modules": [],
        }

    payload_line = _last_non_empty_line(proc.stdout)
    try:
        modules = json.loads(payload_line)
    except json.JSONDecodeError as exc:
        return {
            "returncode": 1,
            "stdout_tail": _tail(proc.stdout),
            "stderr_tail": f"module snapshot parse error: {exc}",
            "modules": [],
        }

    if not isinstance(modules, list):
        return {
            "returncode": 1,
            "stdout_tail": _tail(proc.stdout),
            "stderr_tail": "module snapshot payload was not a list",
            "modules": [],
        }

    normalized_modules = [str(item) for item in modules]
    return {
        "returncode": 0,
        "stdout_tail": "",
        "stderr_tail": _tail(proc.stderr),
        "modules": normalized_modules,
    }


def _heavy_modules(modules: list[str], prefixes: list[str]) -> tuple[list[str], dict[str, int]]:
    heavy_hits: list[str] = []
    prefix_counts: dict[str, int] = {}
    for prefix in prefixes:
        matched = [
            name
            for name in modules
            if name == prefix or name.startswith(f"{prefix}.") or name.startswith(f"{prefix}_")
        ]
        heavy_hits.extend(matched)
        prefix_counts[prefix] = len(matched)
    return heavy_hits, prefix_counts


def _summarize_runs(runs: list[dict[str, Any]]) -> dict[str, Any]:
    durations = [float(run["duration_ms"]) for run in runs if int(run["returncode"]) == 0]
    summary: dict[str, Any] = {
        "runs": runs,
        "successful_runs": len(durations),
        "failed_runs": len(runs) - len(durations),
    }
    if durations:
        summary.update(
            {
                "median": round(statistics.median(durations), 3),
                "mean": round(statistics.fmean(durations), 3),
                "min": round(min(durations), 3),
                "max": round(max(durations), 3),
            }
        )
    else:
        summary.update({"median": None, "mean": None, "min": None, "max": None})
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=5, help="Number of subprocess import timing runs per target.")
    parser.add_argument(
        "--targets",
        nargs="+",
        default=list(DEFAULT_TARGETS),
        help="Target aliases or import paths to measure (default: app analysis_runner).",
    )
    parser.add_argument(
        "--heavy-prefixes",
        nargs="+",
        default=list(DEFAULT_HEAVY_PREFIXES),
        help="Module prefixes to flag in the module snapshot.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_PATH.relative_to(PROJECT_ROOT)),
        help="Timing artifact path (repo-relative or absolute).",
    )
    parser.add_argument(
        "--modules-output",
        default=str(DEFAULT_MODULES_OUTPUT_PATH.relative_to(PROJECT_ROOT)),
        help="Module snapshot artifact path (repo-relative or absolute).",
    )
    parser.add_argument("--timeout-sec", type=int, default=120, help="Per-subprocess timeout in seconds.")
    parser.add_argument("--json", action="store_true", help="Print a concise JSON summary to stdout.")
    args = parser.parse_args()

    repeats = max(1, args.repeats)
    heavy_prefixes = [prefix.strip() for prefix in args.heavy_prefixes if prefix.strip()]
    resolved_targets = [_resolve_target(name) for name in args.targets]
    timing_results: list[dict[str, Any]] = []
    module_results: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    all_ok = True

    for target_name, module_name in resolved_targets:
        runs = [_measure_import(module_name, timeout_sec=args.timeout_sec) for _ in range(repeats)]
        run_summary = _summarize_runs(runs)
        timing_results.append(
            {
                "target": target_name,
                "module": module_name,
                "timing_ms": run_summary,
            }
        )
        if run_summary["failed_runs"]:
            all_ok = False

        snapshot = _capture_modules(module_name, timeout_sec=args.timeout_sec)
        if int(snapshot["returncode"]) != 0:
            all_ok = False
            module_entry = {
                "target": target_name,
                "module": module_name,
                "module_count": 0,
                "heavy_module_count": 0,
                "heavy_prefix_counts": {prefix: 0 for prefix in heavy_prefixes},
                "heavy_modules": [],
                "modules": [],
                "stderr_tail": snapshot["stderr_tail"],
                "stdout_tail": snapshot["stdout_tail"],
            }
        else:
            modules = list(snapshot["modules"])
            heavy_modules, prefix_counts = _heavy_modules(modules, heavy_prefixes)
            module_entry = {
                "target": target_name,
                "module": module_name,
                "module_count": len(modules),
                "heavy_module_count": len(heavy_modules),
                "heavy_prefix_counts": prefix_counts,
                "heavy_modules": heavy_modules,
                "modules": modules,
                "stderr_tail": snapshot["stderr_tail"],
                "stdout_tail": snapshot["stdout_tail"],
            }
        module_results.append(module_entry)
        summary_rows.append(
            {
                "target": target_name,
                "module": module_name,
                "median_ms": run_summary["median"],
                "successful_runs": run_summary["successful_runs"],
                "failed_runs": run_summary["failed_runs"],
                "module_count": module_entry["module_count"],
                "heavy_prefix_counts": module_entry["heavy_prefix_counts"],
            }
        )

    budget_output = _resolve_output_path(args.output)
    modules_output = _resolve_output_path(args.modules_output)
    budget_output.parent.mkdir(parents=True, exist_ok=True)
    modules_output.parent.mkdir(parents=True, exist_ok=True)

    generated_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    budget_report = {
        "generated_at": generated_at,
        "python": sys.executable,
        "repeats": repeats,
        "heavy_prefixes": heavy_prefixes,
        "results": timing_results,
    }
    modules_report = {
        "generated_at": generated_at,
        "python": sys.executable,
        "heavy_prefixes": heavy_prefixes,
        "results": module_results,
    }

    budget_output.write_text(json.dumps(budget_report, ensure_ascii=False, indent=2), encoding="utf-8")
    modules_output.write_text(json.dumps(modules_report, ensure_ascii=False, indent=2), encoding="utf-8")

    stdout_summary = {
        "ok": all_ok,
        "budget_output": str(budget_output.relative_to(PROJECT_ROOT)),
        "modules_output": str(modules_output.relative_to(PROJECT_ROOT)),
        "targets": summary_rows,
    }

    if args.json:
        print(json.dumps(stdout_summary, ensure_ascii=False, indent=2))
    else:
        status = "ok" if all_ok else "fail"
        print(f"[{status}] wrote {stdout_summary['budget_output']} and {stdout_summary['modules_output']}")
        for row in summary_rows:
            print(
                "- {target} ({module}) median={median}ms modules={module_count} heavy={heavy}".format(
                    target=row["target"],
                    module=row["module"],
                    median=row["median_ms"],
                    module_count=row["module_count"],
                    heavy=row["heavy_prefix_counts"],
                )
            )

    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
