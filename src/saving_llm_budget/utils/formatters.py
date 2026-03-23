"""Rendering helpers that use Rich for pretty console output."""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterable, Optional

from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .. import __version__
from ..models import ProviderScore, RoutingDecision

if TYPE_CHECKING:
    from ..services.classifier import ClassificationResult


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


def welcome_banner(
    profile_name: Optional[str] = None,
    profile_summary: Optional[str] = None,
    mode: Optional[str] = None,
    max_budget: Optional[float] = None,
) -> Panel:
    """Welcome banner shown when entering the REPL."""
    table = Table.grid(padding=(0, 1))
    table.add_row("[bold cyan]saving-llm-budget[/bold cyan]", f"[dim]v{__version__}[/dim]")
    table.add_row("[bold]Mode[/bold]", mode or "balanced")
    if max_budget is not None:
        table.add_row("[bold]Budget Cap[/bold]", f"${max_budget:.2f} USD")
    if profile_name:
        table.add_row("[bold]Active Profile[/bold]", profile_summary or profile_name)
    else:
        table.add_row("[bold]Active Profile[/bold]", "[yellow]none — run 'profile add' to configure[/yellow]")
    table.add_row("")
    table.add_row("[dim]Type your task in plain English to get started.[/dim]", "")
    table.add_row("[dim]Special commands: /help  /profile  /history  /override  /exit[/dim]", "")
    return Panel(table, title="[bold]Welcome[/bold]", border_style="cyan", expand=False)


def classification_panel(result: "ClassificationResult") -> Panel:
    """Panel showing what the LLM classified about the task."""
    icon = "[green]AI[/green]" if result.used_llm else "[yellow]heuristic[/yellow]"
    table = Table.grid(padding=(0, 1))
    table.add_row("[bold]Classified by[/bold]", icon)
    table.add_row("[bold]Task type[/bold]", result.task_type.value)
    table.add_row("[bold]Scope[/bold]", result.scope.value)
    table.add_row("[bold]Clarity[/bold]", result.clarity.value)
    table.add_row("[bold]Priority[/bold]", result.priority.value)
    table.add_row("[bold]Long context[/bold]", str(result.long_context))
    table.add_row("[bold]Auto modify[/bold]", str(result.auto_modify))
    table.add_row("[bold]Reasoning[/bold]", result.reasoning)
    return Panel(table, title="Task Classification", border_style="blue", expand=False)


def history_table(history: list[dict]) -> Table:
    """Table showing REPL session history."""
    table = Table(title="Session History", show_lines=True)
    table.add_column("#", justify="right", style="dim", width=3)
    table.add_column("Task", max_width=50)
    table.add_column("Provider", justify="center")
    table.add_column("Confidence", justify="center")
    table.add_column("Status", justify="center")
    for i, entry in enumerate(history, start=1):
        status_color = "green" if entry.get("executed") else "yellow"
        status_text = "executed" if entry.get("executed") else "skipped"
        table.add_row(
            str(i),
            entry.get("description", "")[:50],
            entry.get("provider", "?"),
            f"{entry.get('confidence', 0):.2f}",
            f"[{status_color}]{status_text}[/{status_color}]",
        )
    return table
