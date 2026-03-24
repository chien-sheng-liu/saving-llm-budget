"""Select the specific model to use based on routing decision and task classification."""

from __future__ import annotations

from .. import constants
from ..models import (
    Clarity,
    ComplexityLevel,
    Priority,
    Provider,
    RoutingDecision,
    TaskType,
)
from .classifier import ClassificationResult


def select_model(decision: RoutingDecision, classification: ClassificationResult) -> tuple[str, str]:
    """
    Return (model_id, provider_name) for the given routing decision.

    provider_name is either "anthropic" or "openai".
    """
    provider = decision.provider
    complexity = decision.estimation.complexity
    priority = decision.estimation.cost_level  # use cost_level to respect budget signal

    # Override: if user's priority is explicit, honour it
    task_priority = classification.priority

    if provider in (Provider.CLAUDE, Provider.HYBRID):
        model = _select_claude_model(complexity, task_priority, classification)
        return model, "anthropic"
    else:
        model = _select_openai_model(complexity, task_priority)
        return model, "openai"


def _select_claude_model(
    complexity: ComplexityLevel,
    priority: Priority,
    classification: ClassificationResult,
) -> str:
    # Cheapest override
    if priority == Priority.CHEAPEST:
        return constants.CLAUDE_HAIKU

    # Quality override
    if priority == Priority.BEST_QUALITY:
        return constants.CLAUDE_OPUS

    # Balanced: pick by complexity + task signals
    task_type = classification.task_type
    clarity = classification.clarity

    if (
        complexity == ComplexityLevel.HIGH
        or task_type == TaskType.ARCHITECTURE
        or clarity == Clarity.VERY_AMBIGUOUS
    ):
        return constants.CLAUDE_OPUS

    if complexity == ComplexityLevel.LOW and clarity == Clarity.VERY_CLEAR:
        return constants.CLAUDE_HAIKU

    return constants.CLAUDE_SONNET


def _select_openai_model(complexity: ComplexityLevel, priority: Priority) -> str:
    if priority == Priority.CHEAPEST or complexity == ComplexityLevel.LOW:
        return constants.OPENAI_MINI
    return constants.OPENAI_STANDARD


def estimate_cost(model_id: str, input_tokens: int, output_tokens: int) -> float:
    """Return estimated USD cost for a single call."""
    pricing = constants.MODEL_PRICING.get(model_id)
    if not pricing:
        return 0.0
    input_price, output_price = pricing
    return (input_tokens / 1_000_000) * input_price + (output_tokens / 1_000_000) * output_price
