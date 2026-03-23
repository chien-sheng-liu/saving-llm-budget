"""Data models and enums used across the CLI."""

from __future__ import annotations

from enum import Enum
from typing import List, Optional, Sequence

from pydantic import BaseModel, Field


class TaskType(str, Enum):
    BUGFIX = "bugfix"
    REFACTOR = "refactor"
    FEATURE = "feature"
    ARCHITECTURE = "architecture"
    EXPLAIN = "explain"
    TEST = "test"
    DOCS = "docs"
    REVIEW = "review"


class Scope(str, Enum):
    SINGLE_FILE = "single_file"
    FEW_FILES = "few_files"
    MODULE = "module"
    REPO_WIDE = "repo_wide"


class Clarity(str, Enum):
    VERY_CLEAR = "very_clear"
    SOMEWHAT_AMBIGUOUS = "somewhat_ambiguous"
    VERY_AMBIGUOUS = "very_ambiguous"


class Priority(str, Enum):
    CHEAPEST = "cheapest"
    BALANCED = "balanced"
    BEST_QUALITY = "best_quality"


class ComplexityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Provider(str, Enum):
    CLAUDE = "Claude"
    CODEX = "Codex"
    HYBRID = "Hybrid"


class Workflow(str, Enum):
    DIRECT_CLAUDE = "direct_claude"
    DIRECT_CODEX = "direct_codex"
    PLAN_WITH_CLAUDE_THEN_CODEX = "plan_with_claude_then_execute_with_codex"
    CODEX_THEN_CLAUDE_REVIEW = "codex_then_claude_review"


class TaskRequest(BaseModel):
    """Normalized request payload used by the routing engine."""

    description: str
    task_type: TaskType
    scope: Scope
    clarity: Clarity
    priority: Priority
    long_context: bool = False
    auto_modify: bool = False
    allow_hybrid: bool = True
    repo_path: Optional[str] = None
    benchmark_mode: bool = False


class ProviderScore(BaseModel):
    provider: Provider
    score: float
    contributions: List[str] = Field(default_factory=list)


class RepoSummary(BaseModel):
    root_path: Optional[str] = None
    total_files: Optional[int] = None
    dominant_languages: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)


class DiffSummary(BaseModel):
    files_changed: Optional[int] = None
    insertions: Optional[int] = None
    deletions: Optional[int] = None
    notes: List[str] = Field(default_factory=list)


class BudgetStatus(BaseModel):
    max_budget: float
    estimated_spend: Optional[float] = None
    currency: str = "USD"
    guardrails: List[str] = Field(default_factory=list)


class PolicyDecision(BaseModel):
    enforced: bool = False
    notes: List[str] = Field(default_factory=list)


class BenchmarkReport(BaseModel):
    enabled: bool = False
    notes: List[str] = Field(default_factory=list)
    recommended_checks: List[str] = Field(default_factory=list)


class Estimation(BaseModel):
    complexity: ComplexityLevel
    cost_level: ComplexityLevel
    token_complexity: ComplexityLevel
    notes: List[str] = Field(default_factory=list)


class RoutingDecision(BaseModel):
    provider: Provider
    workflow: Workflow
    confidence: float
    reasoning: str
    estimation: Estimation
    scores: List[ProviderScore]
    suggested_action: str
    cost_note: str
    repo_summary: Optional[RepoSummary] = None
    diff_summary: Optional[DiffSummary] = None
    budget_status: Optional[BudgetStatus] = None
    policy_decisions: List[PolicyDecision] = Field(default_factory=list)
    benchmark_report: Optional[BenchmarkReport] = None


def enum_choices(enum_cls: type[Enum]) -> Sequence[str]:
    """Return the value options for a given Enum."""

    return [member.value for member in enum_cls]
