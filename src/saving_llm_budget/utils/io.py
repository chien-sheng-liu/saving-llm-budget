"""File IO helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml


def read_yaml(path: Path) -> Dict[str, Any]:
    """Read YAML content or return an empty dict."""

    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Unexpected YAML structure in {path}")
    return data


def write_yaml(path: Path, payload: Dict[str, Any]) -> None:
    """Persist YAML content with safe settings."""

    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=True)
