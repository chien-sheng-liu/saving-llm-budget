from saving_llm_budget.config import AppConfig
from saving_llm_budget.models import Clarity, Priority, Provider, Scope, TaskRequest, TaskType
from saving_llm_budget.router.engine import RoutingEngine
from saving_llm_budget.services.estimator import Estimator


def build_config(**overrides):
    defaults = dict(
        default_mode="balanced",
        allow_hybrid=True,
        max_budget_usd=100.0,
    )
    defaults.update(overrides)
    return AppConfig(**defaults)


def test_router_prefers_claude_for_architecture():
    engine = RoutingEngine()
    config = build_config()
    task = TaskRequest(
        description="Design new architecture",
        task_type=TaskType.ARCHITECTURE,
        scope=Scope.REPO_WIDE,
        clarity=Clarity.VERY_AMBIGUOUS,
        priority=Priority.BEST_QUALITY,
        long_context=True,
        auto_modify=False,
        allow_hybrid=True,
    )
    estimation = Estimator().estimate(task)
    decision = engine.route(task, config, estimation)
    assert decision.provider == Provider.CLAUDE
    assert decision.workflow.value == "direct_claude"


def test_router_prefers_codex_for_bugfix():
    engine = RoutingEngine()
    config = build_config()
    task = TaskRequest(
        description="Fix login bug",
        task_type=TaskType.BUGFIX,
        scope=Scope.SINGLE_FILE,
        clarity=Clarity.VERY_CLEAR,
        priority=Priority.CHEAPEST,
        long_context=False,
        auto_modify=True,
        allow_hybrid=True,
    )
    estimation = Estimator().estimate(task)
    decision = engine.route(task, config, estimation)
    assert decision.provider == Provider.CODEX


def test_router_can_choose_hybrid():
    engine = RoutingEngine()
    config = build_config()
    task = TaskRequest(
        description="Implement feature across services",
        task_type=TaskType.FEATURE,
        scope=Scope.MODULE,
        clarity=Clarity.SOMEWHAT_AMBIGUOUS,
        priority=Priority.BALANCED,
        long_context=False,
        auto_modify=False,
        allow_hybrid=True,
    )
    estimation = Estimator().estimate(task)
    decision = engine.route(task, config, estimation)
    assert decision.provider == Provider.HYBRID
