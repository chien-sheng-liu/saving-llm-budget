"""Score aggregation logic for the routing engine."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List

from ..config import AppConfig
from ..models import ComplexityLevel, Estimation, Provider, ProviderScore, TaskRequest
from . import rules


@dataclass
class ScoreAccumulator:
    provider: Provider
    base: float
    contributions: List[str] = field(default_factory=list)

    def add(self, weight: float, description: str) -> None:
        self.base += weight
        self.contributions.append(f"{description} ({weight:+.1f})")

    @property
    def total(self) -> float:
        return self.base

    def to_provider_score(self) -> ProviderScore:
        return ProviderScore(provider=self.provider, score=self.total, contributions=self.contributions)

    def summary(self) -> str:
        if not self.contributions:
            return "Baseline assessment"
        return "; ".join(self.contributions[:3])


class ScoringEngine:
    """Apply weighted heuristic rules to produce provider scores."""

    def __init__(self) -> None:
        self._rules = tuple(rules.iter_rules())

    def score(self, task: TaskRequest, config: AppConfig, estimation: Estimation) -> Dict[Provider, ScoreAccumulator]:
        accumulators = {
            Provider.CLAUDE: ScoreAccumulator(Provider.CLAUDE, base=1.5),
            Provider.CODEX: ScoreAccumulator(Provider.CODEX, base=1.5),
            Provider.HYBRID: ScoreAccumulator(Provider.HYBRID, base=1.0),
        }

        for rule in self._rules:
            if rule.predicate(task, config, estimation):
                accumulators[rule.provider].add(rule.weight, rule.description)

        # Adjust based on estimator output.
        if estimation.token_complexity == ComplexityLevel.HIGH:
            accumulators[Provider.CLAUDE].add(0.9, "High token complexity handled better by Claude")
        elif estimation.token_complexity == ComplexityLevel.LOW:
            accumulators[Provider.CODEX].add(0.6, "Low complexity keeps Codex fast")

        if estimation.cost_level == ComplexityLevel.LOW:
            accumulators[Provider.CODEX].add(0.5, "Low estimated cost aligns with Codex")
        elif estimation.cost_level == ComplexityLevel.HIGH:
            accumulators[Provider.CLAUDE].add(0.4, "Budget available for thoughtful reasoning")

        if estimation.complexity == ComplexityLevel.MEDIUM:
            accumulators[Provider.HYBRID].add(0.3, "Medium complexity suitable for hybrid planning")
        elif estimation.complexity == ComplexityLevel.HIGH:
            accumulators[Provider.CLAUDE].add(0.5, "High overall complexity favors Claude")

        # Enforce provider availability via config.
        if not config.providers.claude.enabled:
            accumulators[Provider.CLAUDE].add(-6.0, "Claude disabled in config")
        if not config.providers.codex.enabled:
            accumulators[Provider.CODEX].add(-6.0, "Codex disabled in config")
        if not config.allow_hybrid or not (config.providers.claude.enabled and config.providers.codex.enabled) or not task.allow_hybrid:
            accumulators[Provider.HYBRID].add(-5.0, "Hybrid workflow disabled")

        return accumulators

    def provider_scores(self, accumulators: Dict[Provider, ScoreAccumulator]) -> List[ProviderScore]:
        return [accumulators[provider].to_provider_score() for provider in Provider]

    def pick_best(self, accumulators: Dict[Provider, ScoreAccumulator]) -> Provider:
        return max(accumulators.values(), key=lambda acc: acc.total).provider

    def confidence(self, accumulators: Dict[Provider, ScoreAccumulator], winner: Provider) -> float:
        totals = [acc.total for acc in accumulators.values()]
        max_total = max(totals)
        exp_values = [math.exp(total - max_total) for total in totals]
        denom = sum(exp_values)
        winner_value = math.exp(accumulators[winner].total - max_total)
        return winner_value / denom if denom else 0.0

    def reasoning(self, accumulator: ScoreAccumulator) -> str:
        return accumulator.summary()
