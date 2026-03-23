"""Policy and budget stubs for future enforcement."""

from __future__ import annotations

from ..config import AppConfig
from ..models import BudgetStatus, ComplexityLevel, Estimation, PolicyDecision, TaskRequest


class BudgetGuardrail:
    """Estimate spend against the configured max budget."""

    COST_BY_LEVEL = {
        ComplexityLevel.LOW: 5.0,
        ComplexityLevel.MEDIUM: 20.0,
        ComplexityLevel.HIGH: 45.0,
    }

    def evaluate(self, config: AppConfig, estimation: Estimation) -> BudgetStatus:
        estimated = self.COST_BY_LEVEL.get(estimation.cost_level, 10.0)
        guardrails: list[str] = []
        if estimated > config.max_budget_usd:
            guardrails.append("Estimated spend exceeds configured max budget")
        return BudgetStatus(
            max_budget=config.max_budget_usd,
            estimated_spend=estimated,
            guardrails=guardrails,
        )


class PolicyEngine:
    """Placeholder policy hooks that can enforce team requirements later."""

    def evaluate(self, task: TaskRequest) -> list[PolicyDecision]:
        if task.benchmark_mode:
            return [
                PolicyDecision(
                    enforced=False,
                    notes=["Benchmark mode active: future releases can enforce plan approvals."],
                )
            ]
        return []
