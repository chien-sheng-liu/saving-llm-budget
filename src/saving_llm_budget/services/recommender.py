"""Service orchestration around the routing engine."""

from __future__ import annotations

from ..config import AppConfig, load_config
from ..models import ProfileMode, RoutingDecision, TaskRequest
from ..router.engine import RoutingEngine
from .estimator import Estimator
from .context import ContextCoordinator


class RoutingService:
    def __init__(
        self,
        engine: RoutingEngine | None = None,
        estimator: Estimator | None = None,
        context_coordinator: ContextCoordinator | None = None,
    ) -> None:
        self.engine = engine or RoutingEngine()
        self.estimator = estimator or Estimator()
        self.context_coordinator = context_coordinator or ContextCoordinator()

    def recommend(
        self,
        task: TaskRequest,
        config: AppConfig | None = None,
        profile_mode: ProfileMode | None = None,
    ) -> RoutingDecision:
        active_config = config or load_config()
        estimation = self.estimator.estimate(task)
        context = self.context_coordinator.build(task, active_config, estimation)
        decision = self.engine.route(task, active_config, estimation)
        return decision.model_copy(
            update={
                "repo_summary": context.repo_summary,
                "diff_summary": context.diff_summary,
                "budget_status": context.budget_status,
                "policy_decisions": context.policy_decisions,
                "benchmark_report": context.benchmark_report,
                "profile_name": task.profile_name,
                "profile_mode": profile_mode,
            }
        )
