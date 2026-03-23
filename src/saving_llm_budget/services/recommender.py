"""Service orchestration around the routing engine."""

from __future__ import annotations

from .. import constants
from ..config import AppConfig, load_config
from ..models import Priority, ProfileMode, RoutingDecision, TaskRequest
from ..router.engine import RoutingEngine
from .classifier import TaskClassifier
from .estimator import Estimator
from .context import ContextCoordinator


class RoutingService:
    def __init__(
        self,
        engine: RoutingEngine | None = None,
        estimator: Estimator | None = None,
        context_coordinator: ContextCoordinator | None = None,
        classifier: TaskClassifier | None = None,
    ) -> None:
        self.engine = engine or RoutingEngine()
        self.estimator = estimator or Estimator()
        self.context_coordinator = context_coordinator or ContextCoordinator()
        self.classifier = classifier or TaskClassifier()

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

    def recommend_from_description(
        self,
        description: str,
        config: AppConfig | None = None,
        profile_mode: ProfileMode | None = None,
        profile_name: str | None = None,
        repo_path: str | None = None,
    ) -> tuple[RoutingDecision, "ClassificationResult"]:  # noqa: F821
        """Classify *description* via LLM then route — returns (decision, classification)."""
        from .classifier import ClassificationResult  # local import avoids circular

        active_config = config or load_config()
        mode_key = active_config.default_mode or constants.DEFAULT_MODE
        default_priority = Priority(
            constants.MODE_TO_PRIORITY.get(mode_key, constants.MODE_TO_PRIORITY[constants.DEFAULT_MODE])
        )

        classification = self.classifier.classify(description)
        task = TaskRequest(
            description=description,
            task_type=classification.task_type,
            scope=classification.scope,
            clarity=classification.clarity,
            priority=classification.priority,
            long_context=classification.long_context,
            auto_modify=classification.auto_modify,
            allow_hybrid=active_config.allow_hybrid,
            repo_path=repo_path,
            benchmark_mode=False,
            profile_name=profile_name,
        )
        decision = self.recommend(task, active_config, profile_mode=profile_mode)
        return decision, classification
