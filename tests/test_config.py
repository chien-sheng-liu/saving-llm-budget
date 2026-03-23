from pathlib import Path

import pytest

from saving_llm_budget import constants
from saving_llm_budget.config import (
    AppConfig,
    ConfigNotFoundError,
    ProviderToggle,
    ProvidersConfig,
    load_config,
    sanitize_mode,
    save_config,
)


def test_save_and_load_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv(constants.CONFIG_ENV_VAR, str(tmp_path))
    config = AppConfig(
        default_mode="quality",
        allow_hybrid=False,
        max_budget_usd=10.0,
        providers=ProvidersConfig(
            claude=ProviderToggle(enabled=False),
            codex=ProviderToggle(enabled=True),
        ),
    )
    path = save_config(config)
    loaded = load_config(path)
    assert loaded == config


def test_load_config_missing(tmp_path):
    with pytest.raises(ConfigNotFoundError):
        load_config(tmp_path / constants.CONFIG_FILE_NAME)


def test_sanitize_mode_defaults():
    assert sanitize_mode("cheap") == "cheap"
    assert sanitize_mode("BALANCED") == "balanced"
    assert sanitize_mode("unknown") == constants.DEFAULT_MODE
