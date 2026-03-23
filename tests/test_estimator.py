from saving_llm_budget.models import Clarity, ComplexityLevel, Priority, Scope, TaskRequest, TaskType
from saving_llm_budget.services.estimator import Estimator


def test_estimator_handles_large_architecture_task():
    estimator = Estimator()
    task = TaskRequest(
        description="Re-architect service mesh",
        task_type=TaskType.ARCHITECTURE,
        scope=Scope.REPO_WIDE,
        clarity=Clarity.VERY_AMBIGUOUS,
        priority=Priority.BEST_QUALITY,
        long_context=True,
        auto_modify=False,
        allow_hybrid=True,
    )
    estimation = estimator.estimate(task)
    assert estimation.complexity == ComplexityLevel.HIGH
    assert estimation.cost_level == ComplexityLevel.HIGH


def test_estimator_marks_simple_bugfix_low_cost():
    estimator = Estimator()
    task = TaskRequest(
        description="Fix typo",
        task_type=TaskType.BUGFIX,
        scope=Scope.SINGLE_FILE,
        clarity=Clarity.VERY_CLEAR,
        priority=Priority.CHEAPEST,
        long_context=False,
        auto_modify=True,
        allow_hybrid=False,
    )
    estimation = estimator.estimate(task)
    assert estimation.complexity == ComplexityLevel.LOW
    assert estimation.cost_level == ComplexityLevel.LOW
