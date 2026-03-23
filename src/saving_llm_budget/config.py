"""Configuration management for saving-llm-budget."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from pydantic import BaseModel, Field, ValidationError

from . import constants
from .utils import io, paths


class ConfigError(Exception):
    """Base exception for config errors."""


class ConfigNotFoundError(ConfigError):
    """Raised when the config file is missing."""

    def __init__(self, path: Path):  # pragma: no cover - trivial
        message = f"Config not found at {path}. Run 'saving-llm-budget init' first."
        super().__init__(message)
        self.path = path


class ProviderToggle(BaseModel):
    enabled: bool = True


class ProvidersConfig(BaseModel):
    claude: ProviderToggle = Field(default_factory=ProviderToggle)
    codex: ProviderToggle = Field(default_factory=ProviderToggle)


class AppConfig(BaseModel):
    default_mode: str = Field(default=constants.DEFAULT_MODE)
    allow_hybrid: bool = Field(default=constants.DEFAULT_ALLOW_HYBRID)
    max_budget_usd: float = Field(default=constants.DEFAULT_MAX_BUDGET_USD, ge=0)
    providers: ProvidersConfig = Field(default_factory=ProvidersConfig)

    def provider_enabled(self, name: str) -> bool:
        data = self.providers.model_dump()
        provider = data.get(name, {})
        return bool(provider.get("enabled", False))


def config_path() -> Path:
    return paths.get_config_path()


def config_exists(path: Path | None = None) -> bool:
    candidate = path or config_path()
    return candidate.exists()


def load_config(path: Path | None = None) -> AppConfig:
    location = path or config_path()
    if not location.exists():
        raise ConfigNotFoundError(location)

    payload = io.read_yaml(location)
    try:
        return AppConfig(**payload)
    except ValidationError as exc:  # pragma: no cover - defensive
        raise ConfigError(f"Invalid config format: {exc}") from exc


def save_config(config: AppConfig, path: Path | None = None) -> Path:
    location = path or config_path()
    paths.ensure_config_directory(location.parent)
    io.write_yaml(location, config.model_dump())
    return location


def default_config_dict() -> Dict[str, Any]:
    return AppConfig().model_dump()


def sanitize_mode(mode: str) -> str:
    normalized = mode.strip().lower()
    if normalized not in constants.MODE_TO_PRIORITY:
        return constants.DEFAULT_MODE
    return normalized
