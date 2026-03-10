"""Safe-lane deprecation + telemetry helpers for compatibility wrappers."""

from __future__ import annotations

import json
import logging
import warnings

from config.settings import settings

logger = logging.getLogger(__name__)

_warned_contracts: set[str] = set()


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
        }
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
