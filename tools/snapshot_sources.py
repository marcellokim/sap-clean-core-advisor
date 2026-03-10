#!/usr/bin/env python3
"""Create source snapshots and optionally refresh catalog snapshot metadata."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.request
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.verify_sources import DEFAULT_CATALOG_PATH, load_source_catalog


def _normalize_domain(domain: str) -> str:
    normalized = domain.strip().lower()
    if normalized.startswith("www."):
        normalized = normalized[4:]
    return normalized


def _fetch_snapshot(url: str, timeout_sec: int = 15) -> bytes:
    req = urllib.request.Request(
        url,
        method="GET",
        headers={"User-Agent": "sap-advisor-source-snapshot/1.0"},
    )
    with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
        return resp.read()


def _fallback_snapshot_html(source: dict[str, Any], captured_at: str, error: str | None = None) -> bytes:
    sid = str(source.get("source_id", "UNKNOWN"))
    title = str(source.get("title", ""))
    url = str(source.get("url", ""))
    error_text = f"<p>fetch_error: {error}</p>" if error else ""
    html = (
        "<html><head><meta charset='utf-8'><title>Source Snapshot</title></head>"
        "<body>"
        f"<h1>{sid}</h1>"
        f"<p>title: {title}</p>"
        f"<p>url: {url}</p>"
        f"<p>captured_at: {captured_at}</p>"
        f"{error_text}"
        "</body></html>"
    )
    return html.encode("utf-8")


def _write_catalog(path: Path, sources: list[dict[str, Any]]) -> None:
    payload = {"sources": sources}
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture snapshots for source catalog entries.")
    parser.add_argument("--path", default=str(DEFAULT_CATALOG_PATH))
    parser.add_argument("--date", default=date.today().isoformat(), help="snapshot date (YYYY-MM-DD)")
    parser.add_argument("--offline", action="store_true", help="skip HTTP fetch and write metadata-only snapshots")
    parser.add_argument("--update-catalog", action="store_true", help="write snapshot_path/hash back to source catalog")
    parser.add_argument("--strict", action="store_true", help="exit non-zero when fetch fails")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        snapshot_date = datetime.strptime(args.date, "%Y-%m-%d").date().isoformat()
    except ValueError:
        print("Invalid --date format. Use YYYY-MM-DD.", file=sys.stderr)
        return 2

    catalog_path = Path(args.path)
    sources = load_source_catalog(catalog_path)
    results: list[dict[str, Any]] = []
    had_fetch_error = False

    for src in sources:
        sid = str(src.get("source_id", "UNKNOWN"))
        url = str(src.get("url", ""))
        out_dir = PROJECT_ROOT / "docs" / "source_snapshots" / sid
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{snapshot_date}.html"

        status = "offline"
        error_message: str | None = None
        if args.offline:
            payload = _fallback_snapshot_html(src, snapshot_date)
        else:
            try:
                payload = _fetch_snapshot(url)
                status = "ok"
            except urllib.error.HTTPError as exc:
                had_fetch_error = True
                status = "fallback"
                error_message = f"http {exc.code}"
                payload = _fallback_snapshot_html(src, snapshot_date, error=error_message)
            except Exception as exc:  # pragma: no cover - defensive
                had_fetch_error = True
                status = "fallback"
                error_message = str(exc)
                payload = _fallback_snapshot_html(src, snapshot_date, error=error_message)

        out_path.write_bytes(payload)
        digest = hashlib.sha256(payload).hexdigest()
        relative_path = out_path.relative_to(PROJECT_ROOT).as_posix()

        src["snapshot_path"] = relative_path
        src["snapshot_hash"] = digest
        src["last_verified_date"] = snapshot_date
        src.setdefault("effective_from", snapshot_date)
        src.setdefault("effective_to", None)
        src.setdefault("jurisdiction", "global")
        src.setdefault("quote_policy", "summary_only")
        if not src.get("publisher_domain"):
            src["publisher_domain"] = _normalize_domain(urlparse(url).netloc.split(":")[0])

        results.append(
            {
                "source_id": sid,
                "status": status,
                "snapshot_path": relative_path,
                "snapshot_hash": digest,
                "error": error_message,
            }
        )

    if args.update_catalog:
        _write_catalog(catalog_path, sources)

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for item in results:
            line = f"{item['source_id']}: {item['status']} -> {item['snapshot_path']}"
            if item["error"]:
                line += f" ({item['error']})"
            print(line)

    if args.strict and had_fetch_error:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

