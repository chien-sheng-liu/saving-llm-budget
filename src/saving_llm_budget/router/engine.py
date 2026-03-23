"""Public routing interface consumed by the CLI."""

from __future__ import annotations

from ..config import AppConfig
from ..models import (
    Estimation,
    Priority,
    Provider,
    RoutingDecision,
    TaskRequest,
    Workflow,
)
from .scorer import ScoringEngine


class RoutingEngine:
    """High-level facade that turns rules and config into a decision."""

    def __init__(self, scorer: ScoringEngine | None = None) -> None:
        self.scorer = scorer or ScoringEngine()

    def route(self, task: TaskRequest, config: AppConfig, estimation: Estimation) -> RoutingDecision:
        accumulators = self.scorer.score(task, config, estimation)
        provider = self.scorer.pick_best(accumulators)
        workflow = self._select_workflow(provider, task)
        confidence = self.scorer.confidence(accumulators, provider)
        reasoning = self.scorer.reasoning(accumulators[provider])
        scores = self.scorer.provider_scores(accumulators)
        suggested_action = self._suggest_action(provider, workflow, task)
        cost_note = self._cost_note(config, estimation)
        return RoutingDecision(
            provider=provider,
            workflow=workflow,
            confidence=confidence,
            reasoning=reasoning,
            estimation=estimation,
            scores=scores,
            suggested_action=suggested_action,
            cost_note=cost_note,
        )

    def _select_workflow(self, provider: Provider, task: TaskRequest) -> Workflow:
        if provider == Provider.CLAUDE:
            return Workflow.DIRECT_CLAUDE
        if provider == Provider.CODEX:
            return Workflow.DIRECT_CODEX
        if task.priority == Priority.BEST_QUALITY:
            return Workflow.CODEX_THEN_CLAUDE_REVIEW
        return Workflow.PLAN_WITH_CLAUDE_THEN_CODEX

    def _suggest_action(self, provider: Provider, workflow: Workflow, task: TaskRequest) -> str:
        if provider == Provider.CLAUDE:
            if workflow == Workflow.DIRECT_CLAUDE:
                return "Open Claude Code with the task context and share the repo map."
        if provider == Provider.CODEX:
            return "Prepare concise instructions and run Codex on the target files."
        if workflow == Workflow.PLAN_WITH_CLAUDE_THEN_CODEX:
            return "Ask Claude for a high-level plan, then execute steps with Codex."
        return "Implement with Codex and request a Claude review pass."

    def _cost_note(self, config: AppConfig, estimation: Estimation) -> str:
        return (
            f"Max budget ${config.max_budget_usd:.2f}; estimated cost level {estimation.cost_level.value}."
        )
