"""Configuration management for saving-llm-budget."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, ValidationError

from . import constants
from .models import ProfileMode, Provider
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


class ProviderProfile(BaseModel):
    provider: Provider
    mode: ProfileMode
    api_keys: list[str] = Field(default_factory=list)
    cli_command: Optional[str] = None


class AppConfig(BaseModel):
    default_mode: str = Field(default=constants.DEFAULT_MODE)
    allow_hybrid: bool = Field(default=constants.DEFAULT_ALLOW_HYBRID)
    max_budget_usd: float = Field(default=constants.DEFAULT_MAX_BUDGET_USD, ge=0)
    providers: ProvidersConfig = Field(default_factory=ProvidersConfig)
    profiles: Dict[str, ProviderProfile] = Field(default_factory=dict)
    active_profile: Optional[str] = None

    def provider_enabled(self, name: str) -> bool:
        data = self.providers.model_dump()
        provider = data.get(name, {})
        return bool(provider.get("enabled", False))

    def get_profile(self, name: str) -> ProviderProfile:
        if name not in self.profiles:
            raise ConfigError(f"Profile '{name}' is not defined.")
        return self.profiles[name]

    def list_profiles(self) -> Dict[str, ProviderProfile]:
        return dict(self.profiles)

    def get_active_profile(self) -> Optional[tuple[str, ProviderProfile]]:
        if self.active_profile and self.active_profile in self.profiles:
            return self.active_profile, self.profiles[self.active_profile]
        return None


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


def upsert_profile(config: AppConfig, name: str, profile: ProviderProfile, set_active: bool = False) -> AppConfig:
    payload = config.model_dump()
    payload.setdefault("profiles", {})[name] = profile.model_dump()
    if set_active or not payload.get("active_profile"):
        payload["active_profile"] = name
    return AppConfig(**payload)


def remove_profile(config: AppConfig, name: str) -> AppConfig:
    if name not in config.profiles:
        raise ConfigError(f"Profile '{name}' does not exist.")
    payload = config.model_dump()
    payload["profiles"].pop(name, None)
    if payload.get("active_profile") == name:
        remaining = payload["profiles"]
        payload["active_profile"] = next(iter(remaining), None) if remaining else None
    return AppConfig(**payload)
