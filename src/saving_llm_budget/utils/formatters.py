"""Rendering helpers that use Rich for pretty console output."""

from __future__ import annotations

from typing import Iterable

from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..models import ProviderScore, RoutingDecision


def decision_panel(decision: RoutingDecision) -> Panel:
    """Build a panel summarizing the routing decision."""

    table = Table.grid(padding=(0, 1))
    table.add_row("[bold]Recommended[/bold]", decision.provider.value)
    table.add_row("[bold]Workflow[/bold]", decision.workflow.value)
    table.add_row("[bold]Confidence[/bold]", f"{decision.confidence:.2f}")
    if decision.profile_name:
        mode = decision.profile_mode.value if decision.profile_mode else "unknown"
        table.add_row("[bold]Profile[/bold]", f"{decision.profile_name} ({mode})")
    table.add_row("[bold]Reasoning[/bold]", decision.reasoning)
    table.add_row("[bold]Suggested Action[/bold]", decision.suggested_action)
    table.add_row("[bold]Cost Note[/bold]", decision.cost_note)
    table.add_row("[bold]Complexity[/bold]", decision.estimation.complexity.value)
    table.add_row("[bold]Token Complexity[/bold]", decision.estimation.token_complexity.value)
    table.add_row("[bold]Estimated Cost Level[/bold]", decision.estimation.cost_level.value)
    if decision.estimation.notes:
        table.add_row("[bold]Estimator Notes[/bold]", "; ".join(decision.estimation.notes))
    if decision.budget_status:
        budget = decision.budget_status
        est_spend = f"${budget.estimated_spend:.2f}" if budget.estimated_spend is not None else "n/a"
        table.add_row("[bold]Budget[/bold]", f"Cap ${budget.max_budget:.2f} vs {est_spend}")
        if budget.guardrails:
            table.add_row("[bold]Budget Guardrails[/bold]", "; ".join(budget.guardrails))
    if decision.repo_summary:
        repo = decision.repo_summary
        languages = ", ".join(repo.dominant_languages) if repo.dominant_languages else "n/a"
        table.add_row("[bold]Repo[/bold]", repo.root_path or "(unknown)")
        if languages != "n/a":
            table.add_row("[bold]Languages[/bold]", languages)
        if repo.notes:
            table.add_row("[bold]Repo Notes[/bold]", "; ".join(repo.notes))
    if decision.diff_summary:
        diff = decision.diff_summary
        meta = f"files {diff.files_changed or 0}, +{diff.insertions or 0}/-{diff.deletions or 0}"
        table.add_row("[bold]Diff Summary[/bold]", meta)
        if diff.notes:
            table.add_row("[bold]Diff Notes[/bold]", "; ".join(diff.notes))
    if decision.policy_decisions:
        combined = "; ".join(" ".join(policy.notes) for policy in decision.policy_decisions if policy.notes)
        if combined:
            table.add_row("[bold]Policy Notes[/bold]", combined)
    if decision.benchmark_report and decision.benchmark_report.enabled:
        table.add_row("[bold]Benchmark[/bold]", "; ".join(decision.benchmark_report.notes))

    return Panel(table, title="Saving LLM Budget Router", expand=False)


def scores_table(scores: Iterable[ProviderScore]) -> Table:
    """Return a Rich table explaining the provider scores."""

    table = Table(title="Score Breakdown")
    table.add_column("Provider", justify="left")
    table.add_column("Total Score", justify="center")
    table.add_column("Contributions", justify="left")

    for score in scores:
        contributions = "\n".join(f"• {item}" for item in score.contributions) or "-"
        table.add_row(score.provider.value, f"{score.score:.2f}", contributions)

    return table


def rules_table(title: str, rows: Iterable[tuple[str, float]]) -> Table:
    table = Table(title=title)
    table.add_column("Description")
    table.add_column("Weight", justify="right")
    for description, weight in rows:
        table.add_row(description, f"{weight:+.2f}")
    return table


def highlight(text: str) -> Text:
    return Text(text, style="bold cyan")
