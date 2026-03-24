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

# ── Model IDs ──────────────────────────────────────────────────────────────────
CLAUDE_HAIKU = "claude-haiku-4-5-20251001"
CLAUDE_SONNET = "claude-sonnet-4-6"
CLAUDE_OPUS = "claude-opus-4-6"

OPENAI_MINI = "gpt-4o-mini"
OPENAI_STANDARD = "gpt-4o"

# ── Pricing: (input $/1M tokens, output $/1M tokens) ──────────────────────────
MODEL_PRICING: dict[str, tuple[float, float]] = {
    CLAUDE_HAIKU:    (0.80,  4.00),
    CLAUDE_SONNET:   (3.00, 15.00),
    CLAUDE_OPUS:    (15.00, 75.00),
    OPENAI_MINI:     (0.15,  0.60),
    OPENAI_STANDARD: (2.50, 10.00),
    # Classifier model (Haiku legacy)
    "claude-3-5-haiku-20241022": (0.80, 4.00),
}

CHAT_MAX_TOKENS = 8192
