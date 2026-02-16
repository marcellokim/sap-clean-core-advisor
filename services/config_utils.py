"""Utilities for loading configuration files used by advisor services.

Note:
    This project stores JSON-compatible payloads in `.yaml` files to avoid
    adding optional parser dependencies. YAML is a superset of JSON.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json_yaml(path: Path) -> dict[str, Any]:
    """Load a JSON-compatible `.yaml` configuration file."""
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"Empty config file: {path}")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        raise ValueError(f"Invalid JSON-compatible YAML at {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Config must be an object: {path}")
    return payload
