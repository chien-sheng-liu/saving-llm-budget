"""Typer CLI wiring for the saving-llm-budget tool."""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import constants, __version__
from .config import (
    AppConfig,
    ConfigNotFoundError,
    ProviderProfile,
    ProviderToggle,
    ProvidersConfig,
    config_exists,
    load_config,
    sanitize_mode,
    save_config,
    upsert_profile,
    remove_profile,
)
from .models import (
    Clarity,
    Priority,
    ProfileMode,
    Scope,
    TaskRequest,
    TaskType,
    Provider,
    enum_choices,
)
from .router import rules
from .services.recommender import RoutingService
from .utils import formatters

app = typer.Typer(add_completion=False, no_args_is_help=True, rich_markup_mode="rich")
profile_app = typer.Typer(help="Manage provider profiles", add_completion=False)
app.add_typer(profile_app, name="profile")
console = Console()
_service = RoutingService()

DEFAULT_API_KEY_ENVS = {
    Provider.CLAUDE: [constants.ANTHROPIC_API_KEY_VAR],
    Provider.CODEX: [constants.OPENAI_API_KEY_VAR],
}


def _require_config() -> AppConfig:
    try:
        return load_config()
    except ConfigNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        console.print("Run [bold]saving-llm-budget init[/bold] to create the config file.")
        raise typer.Exit(code=1) from exc


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context, version: bool = typer.Option(False, "--version", help="Show CLI version.")) -> None:
    if version:
        console.print(f"saving-llm-budget v{__version__}")
        raise typer.Exit()
    if ctx.invoked_subcommand:
        return
    console.print("[bold cyan]saving-llm-budget[/bold cyan] — cost-aware AI coding router")
    console.print("1. Run [bold]saving-llm-budget init[/bold] to create config + first profile (Claude/Codex, API/local).")
    console.print("2. Use [bold]saving-llm-budget ask[/bold] for interactive routing or [bold]run[/bold]/[bold]estimate[/bold] for scripted flows.")
    console.print("3. Manage profiles anytime via [bold]saving-llm-budget profile list[/bold]/add/use/remove.")
    console.print("Need help? Try [bold]saving-llm-budget --help[/bold] or [bold]saving-llm-budget explain[/bold].")
    raise typer.Exit()


def _resolve_profile(config: AppConfig, profile_name: Optional[str]) -> tuple[AppConfig, str, ProviderProfile]:
    profiles = config.list_profiles()
    if not profiles:
        console.print("[red]No provider profiles configured.[/red]")
        console.print(
            "Add one via [bold]saving-llm-budget profile add[/bold] or re-run init to create a quick profile."
        )
        raise typer.Exit(1)

    if profile_name:
        if profile_name not in profiles:
            console.print(f"[red]Profile '{profile_name}' does not exist.[/red]")
            raise typer.Exit(1)
        target = profile_name
    else:
        target = config.active_profile
        if not target or target not in profiles:
            target = next(iter(profiles))
            if config.active_profile != target:
                config = config.model_copy(update={"active_profile": target})
                save_config(config)

    if config.active_profile != target:
        config = config.model_copy(update={"active_profile": target})
        save_config(config)

    profile = config.get_profile(target)
    return config, target, profile


def _profile_summary(profile_name: str, profile: ProviderProfile) -> str:
    mode = "API key" if profile.mode == ProfileMode.API else "local app"
    return f"{profile_name} → {profile.provider.value} via {mode}"


def _profile_wizard(preset_name: Optional[str] = None) -> tuple[str, ProviderProfile]:
    console.print("[bold]Profile setup[/bold]: choose which provider to connect and how.")
    provider = _prompt_enum(
        "Provider",
        Provider,
        Provider.CLAUDE,
        allowed=[Provider.CLAUDE, Provider.CODEX],
    )
    mode = _prompt_enum("Connection mode (api/local_app)", ProfileMode, ProfileMode.API)
    default_name = preset_name or f"{provider.value.lower()}-{mode.value}"
    name = typer.prompt("Profile name", default=default_name).strip()
    if mode == ProfileMode.API:
        defaults = DEFAULT_API_KEY_ENVS.get(provider, [])
        default_env = ",".join(defaults) if defaults else "API_KEY"
        env_input = typer.prompt(
            "Environment variable(s) for the API key (comma separated)", default=default_env
        )
        envs = [item.strip() for item in env_input.split(",") if item.strip()]
        profile = ProviderProfile(provider=provider, mode=mode, api_keys=envs)
    else:
        default_command = "claude" if provider == Provider.CLAUDE else "codex"
        cli_command = typer.prompt("Command that launches the local CLI", default=default_command).strip()
        profile = ProviderProfile(provider=provider, mode=mode, cli_command=cli_command or None)
    return name, profile


def _normalize_choice(value: str) -> str:
    return value.strip().lower().replace(" ", "_").replace("-", "_")


def _prompt_enum(label: str, enum_cls, default, allowed: Optional[list] = None) -> any:
    members = allowed or list(enum_cls)
    option_strings = ", ".join(member.value for member in members)
    default_value = default.value if hasattr(default, "value") else str(default)
    while True:
        value = typer.prompt(f"{label} ({option_strings})", default=default_value)
        normalized = _normalize_choice(value)
        for member in members:
            if normalized in {_normalize_choice(member.value), _normalize_choice(member.name)}:
                return member
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
    profile_name: Optional[str],
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
        profile_name=profile_name,
    )


def _print_decision(decision) -> None:
    console.print(formatters.decision_panel(decision))
    console.print(formatters.scores_table(decision.scores))


@profile_app.command("add", help="Create a new provider profile")
def profile_add() -> None:
    config = _require_config()
    name, profile = _profile_wizard()
    set_active = typer.confirm("Make this the active profile?", default=True)
    config = upsert_profile(config, name, profile, set_active=set_active)
    save_config(config)
    console.print(f"Profile '{name}' saved. {_profile_summary(name, profile)}")


@profile_app.command("list", help="List configured provider profiles")
def profile_list() -> None:
    config = _require_config()
    profiles = config.list_profiles()
    if not profiles:
        console.print("No profiles yet. Run [bold]saving-llm-budget profile add[/bold].")
        return
    table = Table(title="Profiles")
    table.add_column("Name")
    table.add_column("Provider")
    table.add_column("Mode")
    table.add_column("Details")
    table.add_column("Active", justify="center")
    for name, profile in profiles.items():
        detail = ", ".join(profile.api_keys) if profile.api_keys else (profile.cli_command or "-")
        table.add_row(
            name,
            profile.provider.value,
            profile.mode.value,
            detail,
            "✔" if config.active_profile == name else "",
        )
    console.print(table)


@profile_app.command("use", help="Switch the active provider profile")
def profile_use(name: str = typer.Argument(..., help="Profile name to activate")) -> None:
    config = _require_config()
    if name not in config.profiles:
        console.print(f"[red]Profile '{name}' does not exist.[/red]")
        raise typer.Exit(1)
    config = config.model_copy(update={"active_profile": name})
    save_config(config)
    profile = config.get_profile(name)
    console.print(f"Active profile set to {_profile_summary(name, profile)}")


@profile_app.command("remove", help="Delete a profile")
def profile_remove(name: str = typer.Argument(..., help="Profile name to remove")) -> None:
    config = _require_config()
    if name not in config.profiles:
        console.print(f"[red]Profile '{name}' does not exist.[/red]")
        raise typer.Exit(1)
    confirm = typer.confirm(f"Remove profile '{name}'?", default=False)
    if not confirm:
        console.print("Aborted.")
        raise typer.Exit()
    config = remove_profile(config, name)
    save_config(config)
    console.print(f"Profile '{name}' removed.")


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
    if typer.confirm("Create a provider profile now?", default=True):
        profile_name, profile = _profile_wizard()
        config = upsert_profile(config, profile_name, profile, set_active=True)
        console.print(f"Profile '{profile_name}' created and set as active.")
    else:
        console.print(
            "You can add profiles anytime: [bold]saving-llm-budget profile add[/bold]."
        )
    location = save_config(config)
    console.print(f"Config saved to {location}")
    console.print("Next steps: run [bold]saving-llm-budget ask[/bold] for a guided session or [bold]saving-llm-budget profile list[/bold] to review connections.")
    console.print(
        Panel(
            "Set [bold]ANTHROPIC_API_KEY[/bold] and [bold]OPENAI_API_KEY[/bold] in your environment."
            " The tool never transmits them during routing.",
            title="API keys",
        )
    )


@app.command(help="Answer prompts so the router can recommend a provider.")
def ask(
    profile: Optional[str] = typer.Option(None, "--profile", help="Override the active provider profile."),
) -> None:
    config = _require_config()
    config, active_profile_name, active_profile = _resolve_profile(config, profile)
    console.print(f"Using profile {_profile_summary(active_profile_name, active_profile)}")
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
        profile_name=active_profile_name,
    )
    decision = _service.recommend(task, config, profile_mode=active_profile.mode)
    decision = decision.model_copy(
        update={"profile_name": active_profile_name, "profile_mode": active_profile.mode}
    )
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
    profile: Optional[str] = typer.Option(None, "--profile", help="Override the active profile for this run."),
) -> None:
    config = _require_config()
    config, active_profile_name, active_profile = _resolve_profile(config, profile)
    console.print(f"Using profile {_profile_summary(active_profile_name, active_profile)}")
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
        profile_name=active_profile_name,
    )
    decision = _service.recommend(task, config, profile_mode=active_profile.mode)
    decision = decision.model_copy(
        update={"profile_name": active_profile_name, "profile_mode": active_profile.mode}
    )
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
    profile: Optional[str] = typer.Option(None, "--profile", help="Override the active profile."),
) -> None:
    config = _require_config()
    config, active_profile_name, active_profile = _resolve_profile(config, profile)
    console.print(f"Using profile {_profile_summary(active_profile_name, active_profile)}")
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
        profile_name=active_profile_name,
    )
    decision = _service.recommend(task, config, profile_mode=active_profile.mode)
    decision = decision.model_copy(
        update={"profile_name": active_profile_name, "profile_mode": active_profile.mode}
    )

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
