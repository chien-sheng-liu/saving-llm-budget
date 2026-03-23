"""Rule definitions used for scoring."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Iterable, Tuple

from ..config import AppConfig
from ..models import (
    Clarity,
    Estimation,
    Priority,
    Provider,
    Scope,
    TaskRequest,
    TaskType,
)


Predicate = Callable[[TaskRequest, AppConfig, Estimation], bool]


@dataclass(frozen=True)
class Rule:
    name: str
    provider: Provider
    description: str
    weight: float
    predicate: Predicate


RULES: Tuple[Rule, ...] = (
    Rule(
        name="claude_architecture",
        provider=Provider.CLAUDE,
        description="Architecture or strategic planning tasks",
        weight=2.5,
        predicate=lambda task, *_: task.task_type == TaskType.ARCHITECTURE,
    ),
    Rule(
        name="claude_refactor_scope",
        provider=Provider.CLAUDE,
        description="Large refactors favor Claude's holistic reasoning",
        weight=1.2,
        predicate=lambda task, *_: task.task_type == TaskType.REFACTOR
        and task.scope in {Scope.MODULE, Scope.REPO_WIDE},
    ),
    Rule(
        name="claude_repo_scope",
        provider=Provider.CLAUDE,
        description="Module or repo-wide scope benefits from Claude's long context",
        weight=1.3,
        predicate=lambda task, *_: task.scope in {Scope.MODULE, Scope.REPO_WIDE},
    ),
    Rule(
        name="claude_ambiguity_high",
        provider=Provider.CLAUDE,
        description="Highly ambiguous tasks need exploratory reasoning",
        weight=1.5,
        predicate=lambda task, *_: task.clarity == Clarity.VERY_AMBIGUOUS,
    ),
    Rule(
        name="claude_ambiguity_medium",
        provider=Provider.CLAUDE,
        description="Somewhat ambiguous tasks lean toward Claude",
        weight=0.8,
        predicate=lambda task, *_: task.clarity == Clarity.SOMEWHAT_AMBIGUOUS,
    ),
    Rule(
        name="claude_long_context",
        provider=Provider.CLAUDE,
        description="Long context explicitly requested",
        weight=1.6,
        predicate=lambda task, *_: task.long_context,
    ),
    Rule(
        name="claude_quality_priority",
        provider=Provider.CLAUDE,
        description="Quality prioritized over cost",
        weight=1.1,
        predicate=lambda task, *_: task.priority == Priority.BEST_QUALITY,
    ),
    Rule(
        name="claude_review_tasks",
        provider=Provider.CLAUDE,
        description="Review or explanation tasks benefit from Claude",
        weight=1.0,
        predicate=lambda task, *_: task.task_type in {TaskType.REVIEW, TaskType.EXPLAIN},
    ),
    Rule(
        name="codex_bugfix",
        provider=Provider.CODEX,
        description="Bug fixes align well with Codex",
        weight=2.2,
        predicate=lambda task, *_: task.task_type == TaskType.BUGFIX,
    ),
    Rule(
        name="codex_tests",
        provider=Provider.CODEX,
        description="Test or documentation updates are Codex friendly",
        weight=1.4,
        predicate=lambda task, *_: task.task_type in {TaskType.TEST, TaskType.DOCS},
    ),
    Rule(
        name="codex_scope_small",
        provider=Provider.CODEX,
        description="Single or few-file scope keeps Codex efficient",
        weight=1.2,
        predicate=lambda task, *_: task.scope in {Scope.SINGLE_FILE, Scope.FEW_FILES},
    ),
    Rule(
        name="codex_clarity",
        provider=Provider.CODEX,
        description="Very clear instructions enable Codex",
        weight=1.0,
        predicate=lambda task, *_: task.clarity == Clarity.VERY_CLEAR,
    ),
    Rule(
        name="codex_cost_priority",
        provider=Provider.CODEX,
        description="Cost-sensitive priority",
        weight=1.3,
        predicate=lambda task, *_: task.priority == Priority.CHEAPEST,
    ),
    Rule(
        name="codex_auto_modify",
        provider=Provider.CODEX,
        description="Automatic modifications welcomed",
        weight=0.5,
        predicate=lambda task, *_: task.auto_modify,
    ),
    Rule(
        name="codex_penalize_long_context",
        provider=Provider.CODEX,
        description="Long context hurts Codex efficiency",
        weight=-0.8,
        predicate=lambda task, *_: task.long_context,
    ),
    Rule(
        name="hybrid_feature",
        provider=Provider.HYBRID,
        description="Feature work benefits from hybrid planning",
        weight=1.4,
        predicate=lambda task, *_: task.task_type == TaskType.FEATURE,
    ),
    Rule(
        name="hybrid_refactor",
        provider=Provider.HYBRID,
        description="Refactors often need plan + execution",
        weight=1.1,
        predicate=lambda task, *_: task.task_type == TaskType.REFACTOR,
    ),
    Rule(
        name="hybrid_scope",
        provider=Provider.HYBRID,
        description="Module or repo scope encourages hybrid workflows",
        weight=1.0,
        predicate=lambda task, *_: task.scope in {Scope.MODULE, Scope.REPO_WIDE},
    ),
    Rule(
        name="hybrid_ambiguity",
        provider=Provider.HYBRID,
        description="Ambiguity handled well with plan then execute",
        weight=0.7,
        predicate=lambda task, *_: task.clarity != Clarity.VERY_CLEAR,
    ),
    Rule(
        name="hybrid_priority_balanced",
        provider=Provider.HYBRID,
        description="Balanced priority keeps hybrid viable",
        weight=0.4,
        predicate=lambda task, *_: task.priority == Priority.BALANCED,
    ),
)


def grouped_rules() -> Dict[Provider, Tuple[Rule, ...]]:
    mapping: Dict[Provider, list[Rule]] = {provider: [] for provider in Provider}
    for rule in RULES:
        mapping[rule.provider].append(rule)
    return {provider: tuple(items) for provider, items in mapping.items()}


def iter_rules() -> Iterable[Rule]:
    return RULES


def describe_rules() -> Dict[Provider, Tuple[tuple[str, float], ...]]:
    result: Dict[Provider, list[tuple[str, float]]] = {provider: [] for provider in Provider}
    for rule in RULES:
        result[rule.provider].append((rule.description, rule.weight))
    return {provider: tuple(items) for provider, items in result.items()}
