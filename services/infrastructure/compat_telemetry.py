"""Safe-lane deprecation + telemetry helpers for compatibility wrappers."""

from __future__ import annotations

import json
import logging
import sys
import warnings
from datetime import UTC, datetime
from pathlib import Path

from config.settings import settings

logger = logging.getLogger(__name__)

_warned_contracts: set[str] = set()
_REPO_ROOT = Path(__file__).resolve().parents[2]


def _is_test_runtime() -> bool:
    if settings.COMPAT_TELEMETRY_INCLUDE_TESTS:
        return False
    argv = " ".join(sys.argv).lower()
    if "pytest" in argv or "unittest" in argv:
        return True
    return False


def _append_event(payload: dict[str, str]) -> None:
    if _is_test_runtime():
        return
    raw = settings.COMPAT_TELEMETRY_LOG_PATH.strip()
    if not raw:
        return
    path = Path(raw)
    if not path.is_absolute():
        path = _REPO_ROOT / path
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception as exc:  # pragma: no cover - defensive fallback
        logger.warning("compat telemetry append failed: %s", exc)


def mark_compat_usage(
    contract: str,
    replacement: str,
) -> None:
    """Emit compatibility wrapper usage telemetry and deprecation warning."""
    if settings.COMPAT_TELEMETRY_ENABLE:
        payload = {
            "event": "compat_wrapper_used",
            "contract": contract,
            "replacement": replacement,
            "remove_after": settings.COMPAT_DEPRECATION_REMOVE_AFTER,
            "timestamp_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        }
        _append_event(payload)
        logger.info(json.dumps(payload, ensure_ascii=False))

    if not settings.COMPAT_DEPRECATION_WARN:
        return

    if contract in _warned_contracts:
        return
    _warned_contracts.add(contract)
    warnings.warn(
        (
            f"{contract} is deprecated compatibility surface and may be removed after "
            f"{settings.COMPAT_DEPRECATION_REMOVE_AFTER}; use {replacement}."
        ),
        DeprecationWarning,
        stacklevel=2,
    )
