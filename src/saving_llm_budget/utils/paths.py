"""Path helpers for locating config and cache directories."""

from __future__ import annotations

import os
from pathlib import Path

from .. import constants


def get_config_directory() -> Path:
    override = os.getenv(constants.CONFIG_ENV_VAR)
    if override:
        return Path(override).expanduser()
    return Path.home() / constants.CONFIG_DIR_NAME


def ensure_config_directory(directory: Path | None = None) -> Path:
    target = directory or get_config_directory()
    target.mkdir(parents=True, exist_ok=True)
    return target


def get_config_path() -> Path:
    directory = ensure_config_directory()
    return directory / constants.CONFIG_FILE_NAME
