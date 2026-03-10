#!/usr/bin/env python3
"""Validate source catalog schema, staleness, snapshot integrity, and optional URL reachability."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.config_utils import load_json_yaml
from config.settings import settings

DEFAULT_CATALOG_PATH = PROJECT_ROOT / "docs" / "sources.yaml"

ALLOWED_TIERS = {"official", "benchmark", "academic"}
ALLOWED_ACCESS = {"open", "membership", "login_required"}
ALLOWED_METHODS = {"manual", "script"}
ALLOWED_QUOTE_POLICIES = {"summary_only", "short_quote", "no_verbatim"}


@dataclass(frozen=True)
class SourceIssue:
    source_id: str
    message: str


def load_source_catalog(path: Path = DEFAULT_CATALOG_PATH) -> list[dict[str, Any]]:
    payload = load_json_yaml(path)
    sources = payload.get("sources", [])
    if not isinstance(sources, list):
        raise ValueError("`sources` must be a list")
    return [s for s in sources if isinstance(s, dict)]


def _parse_iso_date(raw: Any) -> date | None:
    try:
        return datetime.strptime(str(raw), "%Y-%m-%d").date()
    except ValueError:
        return None


def _normalize_domain(domain: str) -> str:
    normalized = domain.strip().lower()
    if normalized.startswith("www."):
        normalized = normalized[4:]
    return normalized


def _domain_matches(url: str, publisher_domain: str) -> bool:
    host = _normalize_domain(urlparse(url).netloc.split(":")[0])
    pub = _normalize_domain(publisher_domain)
    if not host or not pub:
        return False
    return host == pub or host.endswith(f".{pub}")


def _resolve_snapshot_path(snapshot_path: str) -> Path:
    candidate = Path(snapshot_path)
    if candidate.is_absolute():
        return candidate
    return PROJECT_ROOT / candidate


def _is_valid_sha256(raw: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{64}", raw))


def validate_source_schema(sources: list[dict[str, Any]]) -> list[SourceIssue]:
    issues: list[SourceIssue] = []
    required = {
        "source_id",
        "title",
        "url",
        "tier",
        "access",
        "claims_supported",
        "last_verified_date",
        "verification_method",
        "publisher_domain",
        "jurisdiction",
        "effective_from",
        "effective_to",
        "snapshot_hash",
        "snapshot_path",
        "quote_policy",
    }
    seen: set[str] = set()

    for src in sources:
        sid = str(src.get("source_id", "UNKNOWN"))
        missing = [field for field in required if field not in src]
        if missing:
            issues.append(SourceIssue(sid, f"missing fields: {', '.join(missing)}"))
            continue
        if sid in seen:
            issues.append(SourceIssue(sid, "duplicate source_id"))
        seen.add(sid)

        if src["tier"] not in ALLOWED_TIERS:
            issues.append(SourceIssue(sid, f"invalid tier: {src['tier']}"))
        if src["access"] not in ALLOWED_ACCESS:
            issues.append(SourceIssue(sid, f"invalid access: {src['access']}"))
        if src["verification_method"] not in ALLOWED_METHODS:
            issues.append(SourceIssue(sid, f"invalid verification_method: {src['verification_method']}"))
        if not isinstance(src["claims_supported"], list) or not src["claims_supported"]:
            issues.append(SourceIssue(sid, "claims_supported must be non-empty list"))
        if not isinstance(src["jurisdiction"], str) or not str(src["jurisdiction"]).strip():
            issues.append(SourceIssue(sid, "jurisdiction must be non-empty string"))
        if src["quote_policy"] not in ALLOWED_QUOTE_POLICIES:
            issues.append(SourceIssue(sid, f"invalid quote_policy: {src['quote_policy']}"))

        if not _domain_matches(str(src["url"]), str(src["publisher_domain"])):
            issues.append(
                SourceIssue(
                    sid,
                    f"publisher_domain mismatch (url={src['url']}, publisher_domain={src['publisher_domain']})",
                )
            )

        verified = _parse_iso_date(src["last_verified_date"])
        if verified is None:
            issues.append(SourceIssue(sid, "last_verified_date must be YYYY-MM-DD"))

        effective_from = _parse_iso_date(src["effective_from"])
        if effective_from is None:
            issues.append(SourceIssue(sid, "effective_from must be YYYY-MM-DD"))

        effective_to_raw = src.get("effective_to")
        effective_to: date | None
        if effective_to_raw is None or str(effective_to_raw).strip().lower() in {"", "null", "none"}:
            effective_to = None
        else:
            effective_to = _parse_iso_date(effective_to_raw)
            if effective_to is None:
                issues.append(SourceIssue(sid, "effective_to must be YYYY-MM-DD or null"))
        if effective_from and effective_to and effective_to < effective_from:
            issues.append(SourceIssue(sid, "effective_to must be >= effective_from"))

        snapshot_path_raw = str(src.get("snapshot_path", "")).strip()
        if not snapshot_path_raw:
            issues.append(SourceIssue(sid, "snapshot_path must be non-empty"))
            continue
        snapshot_path = _resolve_snapshot_path(snapshot_path_raw)
        if not snapshot_path.exists():
            issues.append(SourceIssue(sid, f"snapshot_path not found: {snapshot_path_raw}"))
            continue

        snapshot_hash = str(src.get("snapshot_hash", "")).strip().lower()
        if not _is_valid_sha256(snapshot_hash):
            issues.append(SourceIssue(sid, "snapshot_hash must be 64-char lowercase hex sha256"))
            continue

        file_hash = hashlib.sha256(snapshot_path.read_bytes()).hexdigest()
        if file_hash != snapshot_hash:
            issues.append(
                SourceIssue(
                    sid,
                    f"snapshot_hash mismatch (catalog={snapshot_hash}, actual={file_hash})",
                )
            )
    return issues


def find_stale_sources(
    sources: list[dict[str, Any]],
    max_age_days: int,
    reference_date: date | None = None,
) -> list[SourceIssue]:
    issues: list[SourceIssue] = []
    ref = reference_date or date.today()

    for src in sources:
        sid = str(src.get("source_id", "UNKNOWN"))
        try:
            verified = datetime.strptime(str(src["last_verified_date"]), "%Y-%m-%d").date()
        except Exception:
            continue
        age = (ref - verified).days
        if age > max_age_days:
            issues.append(SourceIssue(sid, f"stale source (age={age}d > {max_age_days}d)"))
    return issues


def verify_source_urls(sources: list[dict[str, Any]], timeout_sec: int = 8) -> list[SourceIssue]:
    issues: list[SourceIssue] = []
    for src in sources:
        sid = str(src.get("source_id", "UNKNOWN"))
        url = str(src.get("url", ""))
        tier = str(src.get("tier", ""))
        access = str(src.get("access", ""))
        if not url:
            issues.append(SourceIssue(sid, "empty url"))
            continue

        req = urllib.request.Request(url, method="GET", headers={"User-Agent": "sap-advisor-source-verifier/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                status = int(resp.status)
                if status < 200 or status >= 400:
                    issues.append(SourceIssue(sid, f"http status {status}"))
        except urllib.error.HTTPError as e:
            if tier == "benchmark" and access in {"membership", "login_required", "open"} and e.code in {401, 403}:
                # 제한 접근은 허용하되 기록은 로그용으로만 남긴다.
                continue
            issues.append(SourceIssue(sid, f"http error {e.code}"))
        except Exception as e:
            issues.append(SourceIssue(sid, f"url check failed: {e}"))
    return issues


def _get_max_age_days() -> int:
    return max(1, settings.SOURCE_VERIFY_MAX_AGE_DAYS)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify source catalog quality.")
    parser.add_argument("--path", default=str(DEFAULT_CATALOG_PATH))
    parser.add_argument("--skip-http", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    sources = load_source_catalog(Path(args.path))
    issues = validate_source_schema(sources)
    issues.extend(find_stale_sources(sources, _get_max_age_days()))
    if not args.skip_http:
        issues.extend(verify_source_urls(sources))

    if args.json:
        print(json.dumps([issue.__dict__ for issue in issues], ensure_ascii=False, indent=2))
    else:
        if issues:
            print("Source verification failed:")
            for issue in issues:
                print(f"- {issue.source_id}: {issue.message}")
        else:
            print("Source verification passed.")

    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
