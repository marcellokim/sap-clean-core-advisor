#!/usr/bin/env python3
"""Build compatibility-wrapper telemetry summary for a rolling window."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.settings import settings


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _resolve_log_path(raw: str) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    return ROOT / path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--log-path", default=settings.COMPAT_TELEMETRY_LOG_PATH)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--fail-on-usage", action="store_true")
    parser.add_argument("--require-log", action="store_true")
    args = parser.parse_args()

    now = datetime.now(UTC)
    since = now - timedelta(days=max(1, args.days))
    log_path = _resolve_log_path(args.log_path)

    if not log_path.exists():
        summary = {
            "as_of_utc": now.isoformat().replace("+00:00", "Z"),
            "window_days": args.days,
            "log_path": str(log_path),
            "log_exists": False,
            "total_events_in_window": 0,
            "contracts": {},
            "promotion_ready": True,
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        if args.require_log:
            return 2
        return 0

    counter: Counter[str] = Counter()
    total = 0
    invalid_rows = 0

    with log_path.open("r", encoding="utf-8") as f:
        for line in f:
            row = line.strip()
            if not row:
                continue
            try:
                event = json.loads(row)
            except json.JSONDecodeError:
                invalid_rows += 1
                continue
            timestamp = _parse_ts(event.get("timestamp_utc"))
            if not timestamp or timestamp < since:
                continue
            contract = str(event.get("contract", "")).strip()
            if not contract:
                invalid_rows += 1
                continue
            counter[contract] += 1
            total += 1

    summary = {
        "as_of_utc": now.isoformat().replace("+00:00", "Z"),
        "window_days": args.days,
        "log_path": str(log_path),
        "log_exists": True,
        "total_events_in_window": total,
        "contracts": dict(counter),
        "invalid_rows": invalid_rows,
        "promotion_ready": total == 0,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if args.fail_on_usage and total > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
