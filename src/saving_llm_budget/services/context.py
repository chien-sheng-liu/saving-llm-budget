"""Routing context assembly for future advanced features."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..analysis import GitDiffAnalyzer, RepoScanner
from ..config import AppConfig
from ..models import (
    BenchmarkReport,
    BudgetStatus,
    DiffSummary,
    Estimation,
    PolicyDecision,
    RepoSummary,
    TaskRequest,
)
from .benchmark import BenchmarkService
from .policies import BudgetGuardrail, PolicyEngine


@dataclass
class RoutingContext:
    repo_summary: RepoSummary | None = None
    diff_summary: DiffSummary | None = None
    budget_status: BudgetStatus | None = None
    policy_decisions: list[PolicyDecision] = field(default_factory=list)
    benchmark_report: BenchmarkReport | None = None


class ContextCoordinator:
    """Collects analysis, policy, and budgeting signals."""

    def __init__(
        self,
        repo_scanner: RepoScanner | None = None,
        diff_analyzer: GitDiffAnalyzer | None = None,
        budget_guardrail: BudgetGuardrail | None = None,
        policy_engine: PolicyEngine | None = None,
        benchmark_service: BenchmarkService | None = None,
    ) -> None:
        self.repo_scanner = repo_scanner or RepoScanner()
        self.diff_analyzer = diff_analyzer or GitDiffAnalyzer()
        self.budget_guardrail = budget_guardrail or BudgetGuardrail()
        self.policy_engine = policy_engine or PolicyEngine()
        self.benchmark_service = benchmark_service or BenchmarkService()

    def build(self, task: TaskRequest, config: AppConfig, estimation: Estimation) -> RoutingContext:
        repo_summary = self.repo_scanner.scan(task.repo_path)
        diff_summary = self.diff_analyzer.analyze(task.repo_path)
        budget_status = self.budget_guardrail.evaluate(config, estimation)
        policy_decisions = self.policy_engine.evaluate(task)
        benchmark_report = self.benchmark_service.prepare(task) if task.benchmark_mode else None
        return RoutingContext(
            repo_summary=repo_summary,
            diff_summary=diff_summary,
            budget_status=budget_status,
            policy_decisions=policy_decisions,
            benchmark_report=benchmark_report,
        )
