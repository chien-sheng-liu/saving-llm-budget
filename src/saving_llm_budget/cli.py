"""Typer CLI wiring for the saving-llm-budget tool."""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import constants
from .config import (
    AppConfig,
    ConfigNotFoundError,
    ProviderToggle,
    ProvidersConfig,
    config_exists,
    load_config,
    sanitize_mode,
    save_config,
)
from .models import (
    Clarity,
    Priority,
    Scope,
    TaskRequest,
    TaskType,
    enum_choices,
)
from .router import rules
from .services.recommender import RoutingService
from .utils import formatters

app = typer.Typer(add_completion=False, no_args_is_help=True, rich_markup_mode="rich")
console = Console()
_service = RoutingService()


def _require_config() -> AppConfig:
    try:
        return load_config()
    except ConfigNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        console.print("Run [bold]saving-llm-budget init[/bold] to create the config file.")
        raise typer.Exit(code=1) from exc


def _prompt_enum(label: str, enum_cls, default) -> any:
    options = ", ".join(enum_choices(enum_cls))
    while True:
        value = typer.prompt(f"{label} ({options})", default=default.value)
        normalized = value.strip().lower().replace(" ", "_").replace("-", "_")
        try:
            return enum_cls(normalized)
        except ValueError:
            console.print(f"[red]Invalid choice '{value}'. Try again.[/red]")


def _default_priority(config: AppConfig) -> Priority:
    mode = constants.MODE_TO_PRIORITY.get(config.default_mode, constants.MODE_TO_PRIORITY[constants.DEFAULT_MODE])
    return Priority(mode)


def _build_task_request(
    description: str,
    task_type: TaskType,
    scope: Scope,
    clarity: Clarity,
    priority: Priority,
    long_context: bool,
    auto_modify: bool,
    allow_hybrid: bool,
    repo_path: Optional[str],
    benchmark_mode: bool,
) -> TaskRequest:
    return TaskRequest(
        description=description.strip(),
        task_type=task_type,
        scope=scope,
        clarity=clarity,
        priority=priority,
        long_context=long_context,
        auto_modify=auto_modify,
        allow_hybrid=allow_hybrid,
        repo_path=repo_path,
        benchmark_mode=benchmark_mode,
    )


def _print_decision(decision) -> None:
    console.print(formatters.decision_panel(decision))
    console.print(formatters.scores_table(decision.scores))


@app.command(help="Initialize local configuration and explain credentials.")
def init(force: bool = typer.Option(False, "--force", help="Overwrite existing config without prompting.")) -> None:
    existing = config_exists()
    if existing and not force:
        overwrite = typer.confirm("Config already exists. Overwrite?", default=False)
        if not overwrite:
            console.print("Keeping existing configuration.")
            raise typer.Exit()

    console.print("[bold]Saving LLM Budget setup[/bold]")
    mode = sanitize_mode(
        typer.prompt("Default mode (cheap/balanced/quality)", default=constants.DEFAULT_MODE)
    )
    allow_hybrid = typer.confirm("Allow hybrid workflows?", default=True)
    max_budget = typer.prompt("Max budget (USD)", default="50.0")
    try:
        max_budget_value = float(max_budget)
    except ValueError:
        console.print("[red]Invalid number. Using fallback 50.0[/red]")
        max_budget_value = 50.0
    claude_enabled = typer.confirm("Enable Claude?", default=True)
    codex_enabled = typer.confirm("Enable Codex?", default=True)

    config = AppConfig(
        default_mode=mode,
        allow_hybrid=allow_hybrid,
        max_budget_usd=max_budget_value,
        providers=ProvidersConfig(
            claude=ProviderToggle(enabled=claude_enabled),
            codex=ProviderToggle(enabled=codex_enabled),
        ),
    )
    location = save_config(config)
    console.print(f"Config saved to {location}")
    console.print(
        Panel(
            "Set [bold]ANTHROPIC_API_KEY[/bold] and [bold]OPENAI_API_KEY[/bold] in your environment."
            " The tool never transmits them during routing.",
            title="API keys",
        )
    )


@app.command(help="Answer prompts so the router can recommend a provider.")
def ask() -> None:
    config = _require_config()
    console.print("[bold]Interactive routing[/bold]")
    description = typer.prompt("Task description").strip()
    if not description:
        console.print("[red]Description cannot be empty.[/red]")
        raise typer.Exit(1)

    task_type = _prompt_enum("Task type", TaskType, TaskType.FEATURE)
    scope = _prompt_enum("Scope", Scope, Scope.FEW_FILES)
    clarity = _prompt_enum("Clarity", Clarity, Clarity.SOMEWHAT_AMBIGUOUS)
    priority = _prompt_enum("Priority", Priority, _default_priority(config))
    long_context = typer.confirm("Is long context needed?", default=False)
    auto_modify = typer.confirm("Allow automated file modifications?", default=False)
    repo_path_input = typer.prompt("Repository path (optional)", default="").strip()
    repo_path = repo_path_input or None
    benchmark_mode = typer.confirm("Enable benchmark mode?", default=False)

    task = _build_task_request(
        description=description,
        task_type=task_type,
        scope=scope,
        clarity=clarity,
        priority=priority,
        long_context=long_context,
        auto_modify=auto_modify,
        allow_hybrid=config.allow_hybrid,
        repo_path=repo_path,
        benchmark_mode=benchmark_mode,
    )
    decision = _service.recommend(task, config)
    _print_decision(decision)


@app.command(help="Non-interactive routing for scripts or quick checks.")
def run(
    task_description: str = typer.Argument(..., help="Describe the coding task."),
    task_type: Optional[TaskType] = typer.Option(None, "--task-type", case_sensitive=False),
    scope: Optional[Scope] = typer.Option(None, "--scope", case_sensitive=False),
    clarity: Optional[Clarity] = typer.Option(None, "--clarity", case_sensitive=False),
    priority: Optional[Priority] = typer.Option(None, "--priority", case_sensitive=False),
    long_context: Optional[bool] = typer.Option(None, "--long-context/--no-long-context", help="Does the task need extended context?"),
    auto_modify: Optional[bool] = typer.Option(None, "--auto-modify/--no-auto-modify", help="Allow the agent to change files automatically."),
    repo_path: Optional[str] = typer.Option(None, "--repo-path", help="Path to the repository for future scanning."),
    benchmark_mode: bool = typer.Option(False, "--benchmark/--no-benchmark", help="Toggle benchmark oriented reporting."),
) -> None:
    config = _require_config()
    task = _build_task_request(
        description=task_description,
        task_type=task_type or TaskType.FEATURE,
        scope=scope or Scope.FEW_FILES,
        clarity=clarity or Clarity.SOMEWHAT_AMBIGUOUS,
        priority=priority or _default_priority(config),
        long_context=bool(long_context) if long_context is not None else False,
        auto_modify=bool(auto_modify) if auto_modify is not None else False,
        allow_hybrid=config.allow_hybrid,
        repo_path=repo_path,
        benchmark_mode=benchmark_mode,
    )
    decision = _service.recommend(task, config)
    _print_decision(decision)


@app.command(help="Explain the scoring rules that power routing decisions.")
def explain() -> None:
    console.rule("Routing logic overview")
    console.print(
        "Scores combine weighted rules, config toggles, and estimator output."
        " Higher scores win, and we convert the spread into a confidence metric."
    )
    for provider, entries in rules.describe_rules().items():
        console.print(formatters.rules_table(f"{provider.value} rules", entries))


@app.command(help="Estimate task complexity, cost level, and recommendation.")
def estimate(
    task_description: str = typer.Argument(..., help="Describe the task to estimate."),
    task_type: Optional[TaskType] = typer.Option(None, "--task-type", case_sensitive=False),
    scope: Optional[Scope] = typer.Option(None, "--scope", case_sensitive=False),
    clarity: Optional[Clarity] = typer.Option(None, "--clarity", case_sensitive=False),
    priority: Optional[Priority] = typer.Option(None, "--priority", case_sensitive=False),
    long_context: Optional[bool] = typer.Option(None, "--long-context/--no-long-context"),
    auto_modify: Optional[bool] = typer.Option(None, "--auto-modify/--no-auto-modify"),
    repo_path: Optional[str] = typer.Option(None, "--repo-path"),
    benchmark_mode: bool = typer.Option(False, "--benchmark/--no-benchmark"),
) -> None:
    config = _require_config()
    task = _build_task_request(
        description=task_description,
        task_type=task_type or TaskType.FEATURE,
        scope=scope or Scope.FEW_FILES,
        clarity=clarity or Clarity.SOMEWHAT_AMBIGUOUS,
        priority=priority or _default_priority(config),
        long_context=bool(long_context) if long_context is not None else False,
        auto_modify=bool(auto_modify) if auto_modify is not None else False,
        allow_hybrid=config.allow_hybrid,
        repo_path=repo_path,
        benchmark_mode=benchmark_mode,
    )
    decision = _service.recommend(task, config)

    table = Table(title="Estimate")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Complexity", decision.estimation.complexity.value)
    table.add_row("Token Complexity", decision.estimation.token_complexity.value)
    table.add_row("Estimated Cost", decision.estimation.cost_level.value)
    table.add_row("Provider", decision.provider.value)
    table.add_row("Workflow", decision.workflow.value)
    table.add_row("Confidence", f"{decision.confidence:.2f}")
    console.print(table)


__all__ = ["app"]
