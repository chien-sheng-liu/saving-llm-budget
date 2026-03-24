"""Typer CLI wiring for the saving-llm-budget tool."""

from __future__ import annotations

import os
import subprocess
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
from .providers.executor import ProviderExecutor
from .services.recommender import RoutingService
from .services.tester import TestRunner
from .utils import formatters

app = typer.Typer(add_completion=False, no_args_is_help=True, rich_markup_mode="rich")
profile_app = typer.Typer(help="Manage provider profiles", add_completion=False)
app.add_typer(profile_app, name="profile")
console = Console()
_service = RoutingService()
_test_runner = TestRunner(console)
_executor = ProviderExecutor(console)

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


def _resolve_profile(
    config: AppConfig, profile_name: Optional[str]
) -> tuple[AppConfig, Optional[str], Optional[ProviderProfile]]:
    config = _auto_profiles_from_env(config)
    profiles = config.list_profiles()
    if not profiles:
        if profile_name:
            console.print(f"[red]Profile '{profile_name}' does not exist.[/red]")
            raise typer.Exit(1)
        console.print(
            "[yellow]No provider profiles configured yet. You can continue without one[/yellow]"
            " or create it now."
        )
        if typer.confirm("Create a profile now?", default=True):
            name, new_profile = _profile_wizard()
            config = upsert_profile(config, name, new_profile, set_active=True)
            save_config(config)
            return config, name, new_profile
        console.print(
            "Continuing without a provider profile. (Add one later via"
            " [bold]saving-llm-budget profile add[/bold].)"
        )
        return config, None, None

    if profile_name:
        if profile_name not in profiles:
            console.print(f"[red]Profile '{profile_name}' does not exist.[/red]")
            raise typer.Exit(1)
        target = profile_name
    else:
        target = config.active_profile or next(iter(profiles))
        if config.active_profile != target:
            config = config.model_copy(update={"active_profile": target})
            save_config(config)

    profile = config.get_profile(target)
    return config, target, profile


def _profile_summary(profile_name: Optional[str], profile: Optional[ProviderProfile]) -> str:
    if not profile or not profile_name:
        return "(no provider profile)"
    provider_value = profile.provider.value if hasattr(profile.provider, "value") else str(profile.provider)
    mode_value = profile.mode.value if hasattr(profile.mode, "value") else str(profile.mode)
    mode_label = "API key" if mode_value == ProfileMode.API.value else "local app"
    return f"{profile_name} → {provider_value} via {mode_label}"


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


def _auto_profiles_from_env(config: AppConfig) -> AppConfig:
    updated = config

    def ensure(name: str, provider: Provider, env_var: str) -> None:
        nonlocal updated
        if not os.getenv(env_var):
            return
        if name in updated.profiles:
            return
        profile = ProviderProfile(provider=provider, mode=ProfileMode.API, api_keys=[env_var])
        updated = upsert_profile(updated, name, profile, set_active=False)
        save_config(updated)
        console.print(
            f"Auto-detected {env_var}; created profile '{name}' tied to that environment variable."
        )

    ensure("claude-auto", Provider.CLAUDE, constants.ANTHROPIC_API_KEY_VAR)
    ensure("codex-auto", Provider.CODEX, constants.OPENAI_API_KEY_VAR)

    if not updated.active_profile and updated.profiles:
        first = next(iter(updated.profiles))
        updated = updated.model_copy(update={"active_profile": first})
        save_config(updated)

    return updated


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


def _maybe_execute(task: TaskRequest, profile: Optional[ProviderProfile], prompt: bool = True) -> None:
    if profile is None:
        return
    if prompt:
        confirm = typer.confirm(
            f"Execute task via {profile.provider.value} ({profile.mode.value}) now?", default=True
        )
        if not confirm:
            return
    _executor.execute(task, profile)


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

    config = AppConfig(
        default_mode=mode,
        allow_hybrid=allow_hybrid,
        max_budget_usd=max_budget_value,
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
    if typer.confirm("Start the interactive console now?", default=True):
        console_loop()


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
    profile_mode = active_profile.mode if active_profile else None
    decision = _service.recommend(task, config, profile_mode=profile_mode)
    decision = decision.model_copy(update={"profile_name": active_profile_name, "profile_mode": profile_mode})
    _print_decision(decision)
    _maybe_execute(task, active_profile)


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
    profile_mode = active_profile.mode if active_profile else None
    decision = _service.recommend(task, config, profile_mode=profile_mode)
    decision = decision.model_copy(update={"profile_name": active_profile_name, "profile_mode": profile_mode})
    _print_decision(decision)
    _maybe_execute(task, active_profile)


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
    profile_mode = active_profile.mode if active_profile else None
    decision = _service.recommend(task, config, profile_mode=profile_mode)
    decision = decision.model_copy(update={"profile_name": active_profile_name, "profile_mode": profile_mode})

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
    _maybe_execute(task, active_profile, prompt=False)


@app.command(help="Run the local pytest suite with a friendly interface.")
def test(
    target: Optional[str] = typer.Argument(None, help="Optional test path or expression."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Pass -vv to pytest."),
    last_failed: bool = typer.Option(False, "--last-failed", help="Re-run only failed tests."),
) -> None:
    args: list[str] = []
    if verbose:
        args.append("-vv")
    if last_failed:
        args.append("--last-failed")
    if target:
        args.append(target)
    console.print("[bold]Executing pytest[/bold]")
    result = _test_runner.run(args)
    status = "passed" if result.success else "failed"
    panel = Panel(
        f"Command: {' '.join(result.command)}\n"
        f"Status: {status}\n"
        f"Duration: {result.duration:.2f}s\n"
        f"Exit code: {result.return_code}",
        title="Test Summary",
        style="green" if result.success else "red",
    )
    console.print(panel)
    if result.stdout:
        console.rule("stdout")
        console.print(result.stdout.rstrip())
    if result.stderr:
        console.rule("stderr")
        console.print(result.stderr.rstrip())
    if not result.success:
        raise typer.Exit(result.return_code)


@app.command(name="console", help="Start a persistent AI-powered REPL — type tasks in plain English.")
def console_loop(
    profile: Optional[str] = typer.Option(None, "--profile", help="Override the active provider profile."),
) -> None:
    from .repl import ReplSession

    config = _require_config()
    config, active_profile_name, active_profile = _resolve_profile(config, profile)
    session = ReplSession(
        config=config,
        profile_name=active_profile_name,
        profile=active_profile,
        executor=_executor,
        service=_service,
        console=console,
    )
    session.run()


@app.command(name="chat", help="Auto-routing chat — type a prompt and the best model is picked for you.")
def chat_cmd(
    anthropic_key: Optional[str] = typer.Option(
        None, "--anthropic-key", envvar="ANTHROPIC_API_KEY",
        help="Anthropic API key (or set ANTHROPIC_API_KEY).",
    ),
    openai_key: Optional[str] = typer.Option(
        None, "--openai-key", envvar="OPENAI_API_KEY",
        help="OpenAI API key (or set OPENAI_API_KEY).",
    ),
) -> None:
    from .chat import ChatSession

    needs_key_prompt = not anthropic_key and not openai_key

    if needs_key_prompt:
        console.print(
            Panel(
                "[bold]slb chat[/bold] needs at least one API key to get started.\n\n"
                "Keys are sent directly to the provider API and [bold]never stored to disk[/bold].\n"
                "To skip this prompt in future sessions, export them in your shell:\n\n"
                "  [dim]export ANTHROPIC_API_KEY=\"sk-ant-...\"[/dim]\n"
                "  [dim]export OPENAI_API_KEY=\"sk-proj-...\"[/dim]",
                border_style="cyan",
                padding=(1, 3),
            )
        )

    if not anthropic_key:
        anthropic_key = typer.prompt(
            "Anthropic API key  [dim](Claude models — blank to skip)[/dim]",
            default="",
            hide_input=True,
            prompt_suffix="\n  › ",
        )

    if not openai_key:
        openai_key = typer.prompt(
            "OpenAI API key  [dim](GPT models — blank to skip)[/dim]",
            default="",
            hide_input=True,
            prompt_suffix="\n  › ",
        )

    if not anthropic_key and not openai_key:
        console.print(
            "\n[red]  No API key provided.[/red]  "
            "At least one key (Anthropic or OpenAI) is required.\n"
            "  Get yours at [link]https://console.anthropic.com[/link] "
            "or [link]https://platform.openai.com[/link]."
        )
        raise typer.Exit(code=1)

    try:
        config = load_config()
    except ConfigNotFoundError:
        config = None  # type: ignore[assignment]

    session = ChatSession(
        anthropic_key=anthropic_key,
        openai_key=openai_key,
        config=config,
    )
    session.run()


@app.command(name="setup", help="Check your environment and install Claude Code / Codex CLI.")
def setup_cmd() -> None:
    from .setup_wizard import run_setup_wizard
    run_setup_wizard(console)


@app.command(name="do", help="Route your task to Claude Code or Codex and dispatch it.")
def do_cmd(
    task: str = typer.Argument(..., help="What you want to do, in plain English."),
    repo_path: Optional[str] = typer.Option(
        None, "--repo", "-r", help="Path to the repository (defaults to current directory)."
    ),
    auto_install: bool = typer.Option(
        True, "--auto-install/--no-auto-install",
        help="Offer to install missing CLI tools automatically.",
    ),
    anthropic_key: Optional[str] = typer.Option(
        None, "--anthropic-key", envvar="ANTHROPIC_API_KEY",
        help="Anthropic API key — used for LLM routing and API fallback.",
    ),
    openai_key: Optional[str] = typer.Option(
        None, "--openai-key", envvar="OPENAI_API_KEY",
        help="OpenAI API key — used for API fallback when Codex CLI is unavailable.",
    ),
) -> None:
    """
    Route your task with LLM judgement and dispatch to the right CLI tool.

      slb do "Fix the null pointer in UserService"
      slb do "Redesign the auth module" --repo ./backend
    """
    from .services.llm_router import LLMRouter, SessionCost
    from .setup_wizard import ensure_tool, TOOLS
    from .models import Provider, TaskRequest
    from .config import ProviderProfile, ProfileMode

    # ── 0. Load (or create) config ─────────────────────────────────────────────
    try:
        config = load_config()
    except ConfigNotFoundError:
        config = AppConfig()

    # ── 1. First-run: ask routing preference if not set ────────────────────────
    if config.routing_mode is None:
        console.print(
            Panel(
                "[bold]How should slb choose between Claude Code and Codex?[/bold]\n\n"
                "  [cyan]auto[/cyan]  — LLM decides and dispatches immediately [dim](recommended)[/dim]\n"
                "  [cyan]ask[/cyan]   — LLM recommends, you confirm before each dispatch\n",
                border_style="cyan",
                padding=(1, 3),
            )
        )
        raw = typer.prompt(
            "Routing mode",
            default="auto",
            prompt_suffix="\n  › ",
        ).strip().lower()
        routing_mode = "ask" if raw.startswith("a") and "s" in raw else "auto"
        config = config.model_copy(update={"routing_mode": routing_mode})
        save_config(config)
        console.print(
            f"\n  [dim]Saved: routing_mode = [bold]{routing_mode}[/bold]"
            "  (change anytime with [bold]slb config[/bold])[/dim]\n"
        )

    routing_mode = config.routing_mode or "auto"
    session_cost = SessionCost()

    # ── 2. LLM routing ─────────────────────────────────────────────────────────
    router = LLMRouter(api_key=anthropic_key or "")
    try:
        with console.status("[dim]Thinking about which tool fits best…[/dim]", spinner="dots"):
            decision = router.route(task)
    except Exception as exc:
        console.print(f"[red]Routing error: {exc}[/red]")
        raise typer.Exit(1) from exc

    session_cost.add(decision)

    tool_name  = decision.tool                            # "claude" or "codex"
    tool_label = "Claude Code" if tool_name == "claude" else "Codex"
    style      = "blue" if tool_name == "claude" else "green"
    conf_pct   = int(decision.confidence * 100)
    llm_badge  = "[dim]LLM[/dim]" if decision.used_llm else "[dim]heuristic[/dim]"

    console.print(
        f"\n  [{style}]⚡ {tool_label}[/{style}]"
        f"  [dim]{conf_pct}% conf  ·  {llm_badge}[/dim]\n"
        f"  [dim italic]{decision.reasoning}[/dim italic]\n"
    )

    if decision.used_llm:
        console.print(
            f"  [dim]Routing: {decision.input_tokens} in / "
            f"{decision.output_tokens} out  ·  ${decision.cost_usd:.5f}[/dim]\n"
        )

    # ── 3. "ask" mode: confirm before dispatch ─────────────────────────────────
    if routing_mode == "ask":
        other = "codex" if tool_name == "claude" else "claude"
        other_label = "Codex" if other == "codex" else "Claude Code"
        console.print(
            f"  Dispatch to [bold]{tool_label}[/bold]?  "
            f"([cyan]y[/cyan]=yes  [cyan]n[/cyan]=use {other_label}  [cyan]q[/cyan]=quit)"
        )
        answer = typer.prompt("", default="y", prompt_suffix=" › ").strip().lower()
        if answer.startswith("q"):
            console.print("[dim]  Aborted.[/dim]")
            raise typer.Exit(0)
        if answer.startswith("n"):
            tool_name  = other
            tool_label = other_label
            style      = "green" if tool_name == "codex" else "blue"
            console.print(f"\n  [dim]Switching to [bold]{tool_label}[/bold].[/dim]\n")

    # ── 4. Ensure the tool is installed ───────────────────────────────────────
    tool_ok = ensure_tool(tool_name, console, auto_install=auto_install)

    if not tool_ok:
        other = "codex" if tool_name == "claude" else "claude"
        console.print(f"\n  [yellow]Trying {TOOLS[other]['label']} as fallback…[/yellow]")
        tool_ok = ensure_tool(other, console, auto_install=auto_install)
        if tool_ok:
            tool_name  = other
            tool_label = TOOLS[other]["label"]

    if not tool_ok:
        console.print(
            Panel(
                "[yellow]No CLI tools available.[/yellow]\n\n"
                "Falling back to direct API call.\n"
                "Run [bold]slb setup[/bold] to install Claude Code or Codex.",
                border_style="yellow",
                padding=(0, 2),
            )
        )
        from .chat import ChatSession
        if not anthropic_key and not openai_key:
            console.print(
                "[red]  No API keys available either.[/red]  "
                "Set [bold]ANTHROPIC_API_KEY[/bold] or [bold]OPENAI_API_KEY[/bold]."
            )
            raise typer.Exit(1)
        session = ChatSession(
            anthropic_key=anthropic_key or "",
            openai_key=openai_key or "",
            config=config,
        )
        session._process(task)
        _print_session_cost(console, session_cost)
        session._print_farewell()
        return

    # ── 5. Dispatch ────────────────────────────────────────────────────────────
    tr = TaskRequest(
        description=task,
        task_type=_task_type_from_tool(tool_name),
        scope=__import__("saving_llm_budget.models", fromlist=["Scope"]).Scope.FEW_FILES,
        clarity=__import__("saving_llm_budget.models", fromlist=["Clarity"]).Clarity.SOMEWHAT_AMBIGUOUS,
        priority=__import__("saving_llm_budget.models", fromlist=["Priority"]).Priority.BALANCED,
        long_context=False,
        auto_modify=True,
        repo_path=repo_path or ".",
    )
    profile = ProviderProfile(
        provider=Provider.CLAUDE if tool_name == "claude" else Provider.CODEX,
        mode=ProfileMode.LOCAL_APP,
        cli_command=tool_name,
    )

    exit_code = _executor.execute(tr, profile)
    _print_session_cost(console, session_cost)
    raise typer.Exit(exit_code)


def _task_type_from_tool(tool_name: str):
    from .models import TaskType
    return TaskType.FEATURE


def _print_session_cost(console: Console, session_cost) -> None:
    from .services.llm_router import SessionCost
    if session_cost.calls == 0:
        return
    console.print(
        f"\n[dim]  Session routing cost: {session_cost.summary()}[/dim]"
    )
    console.print(
        "[dim]  Note: tokens used by Claude Code / Codex CLI are billed directly "
        "to your provider account.[/dim]"
    )


__all__ = ["app"]
