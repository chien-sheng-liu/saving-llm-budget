"""Global constants for the saving-llm-budget project."""

from __future__ import annotations

CONFIG_DIR_NAME = ".saving-llm-budget"
CONFIG_FILE_NAME = "config.yaml"
CONFIG_ENV_VAR = "SAVING_LLM_BUDGET_CONFIG_DIR"
ANTHROPIC_API_KEY_VAR = "ANTHROPIC_API_KEY"
OPENAI_API_KEY_VAR = "OPENAI_API_KEY"

DEFAULT_MODE = "balanced"
DEFAULT_MAX_BUDGET_USD = 50.0
DEFAULT_ALLOW_HYBRID = True
DEFAULT_PROVIDER_FLAGS = {
    "claude": {"enabled": True},
    "codex": {"enabled": True},
}

MODE_TO_PRIORITY = {
    "cheap": "cheapest",
    "balanced": "balanced",
    "quality": "best_quality",
}

# LLM classifier settings (uses cheap Haiku for fast task analysis)
CLASSIFIER_MODEL = "claude-3-5-haiku-20241022"
CLASSIFIER_MAX_TOKENS = 512
CLASSIFIER_TEMPERATURE = 0.0
