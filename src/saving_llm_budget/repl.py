"""Persistent REPL session with LLM-powered task classification and routing."""

from __future__ import annotations

import os
from typing import Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text

from .config import AppConfig, ProviderProfile, load_config
from .models import Clarity, Priority, Scope, TaskType
from .providers.executor import ProviderExecutor
from .services.recommender import RoutingService
from .utils import formatters


_PROMPT_STYLE = Style.from_dict(
    {
        "prompt": "bold ansigreen",
    }
)

_HELP_TEXT = """
[bold cyan]Available commands:[/bold cyan]

  [bold]/help[/bold]       Show this help message
  [bold]/profile[/bold]    Show the active profile details
  [bold]/history[/bold]    Show tasks submitted in this session
  [bold]/override[/bold]   After classification, manually adjust task fields before routing
  [bold]/exit[/bold]       Exit the REPL (also: quit, exit, Ctrl+D)

[bold cyan]Task input:[/bold cyan]

  Just type your task in plain English and press Enter.
  The AI will classify the task and recommend the best provider.
  You will be asked to confirm before execution.

[dim]Examples:[/dim]
  Fix the null pointer in UserService line 42
  Refactor the authentication module to use JWT
  Add unit tests for the payment service
"""


class ReplSession:
    """Interactive REPL that stays running between tasks."""

    def __init__(
        self,
        config: AppConfig,
        profile_name: Optional[str],
        profile: Optional[ProviderProfile],
        service: Optional[RoutingService] = None,
        executor: Optional[ProviderExecutor] = None,
        console: Optional[Console] = None,
    ) -> None:
        self.config = config
        self.profile_name = profile_name
        self.profile = profile
        self.service = service or RoutingService()
        self.executor = executor or ProviderExecutor()
        self.console = console or Console()
        self._history: list[dict] = []
        self._pending_override: Optional[dict] = None

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Start the REPL loop."""
        self.console.print(
            formatters.welcome_banner(
                profile_name=self.profile_name,
                profile_summary=self._profile_summary(),
                mode=self.config.default_mode,
                max_budget=self.config.max_budget_usd,
            )
        )

        session: PromptSession = PromptSession(
            history=InMemoryHistory(),
            style=_PROMPT_STYLE,
        )

        while True:
            try:
                raw = session.prompt([("class:prompt", "slb> ")]).strip()
            except (EOFError, KeyboardInterrupt):
                self.console.print("\n[dim]Bye![/dim]")
                break

            if not raw:
                continue

            if raw.lower() in {"exit", "quit", "/exit", "/quit"}:
                self.console.print("[dim]Bye![/dim]")
                break

            if raw.startswith("/"):
                self._handle_command(raw)
            else:
                self._handle_task(raw)

    # ------------------------------------------------------------------
    # Command handlers
    # ------------------------------------------------------------------

    def _handle_command(self, raw: str) -> None:
        cmd = raw.split()[0].lower()
        if cmd in {"/help", "/h"}:
            self.console.print(_HELP_TEXT)
        elif cmd in {"/profile"}:
            self._show_profile()
        elif cmd in {"/history"}:
            self._show_history()
        elif cmd in {"/override"}:
            self.console.print(
                "[yellow]Use /override after submitting a task — it applies to the next classification.[/yellow]"
            )
        else:
            self.console.print(f"[red]Unknown command: {cmd}[/red]  Type [bold]/help[/bold] for options.")

    def _show_profile(self) -> None:
        if not self.profile or not self.profile_name:
            self.console.print("[yellow]No active profile. Run `saving-llm-budget profile add`.[/yellow]")
            return
        self.console.print(
            f"[bold]Active profile:[/bold] {self.profile_name}\n"
            f"  Provider : {self.profile.provider.value}\n"
            f"  Mode     : {self.profile.mode.value}\n"
            f"  Command  : {self.profile.cli_command or ', '.join(self.profile.api_keys or [])}"
        )

    def _show_history(self) -> None:
        if not self._history:
            self.console.print("[dim]No tasks submitted yet in this session.[/dim]")
            return
        self.console.print(formatters.history_table(self._history))

    # ------------------------------------------------------------------
    # Task flow: classify → route → confirm → execute
    # ------------------------------------------------------------------

    def _handle_task(self, description: str) -> None:
        from .services.llm_router import LLMRouter
        from .config import ProviderProfile
        from .models import ProfileMode, Provider

        anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")

        # ── Route ─────────────────────────────────────────────────────────────
        router = LLMRouter(api_key=anthropic_key)
        try:
            with Live(
                Spinner("dots", text=Text(" Routing...", style="dim")),
                console=self.console,
                refresh_per_second=10,
                transient=True,
            ):
                decision = router.route(description)
        except Exception as exc:  # noqa: BLE001
            self.console.print(f"[red]Routing error: {exc}[/red]")
            return

        tool_name = decision.tool  # "claude" or "codex"
        tool_label = "Claude Code" if tool_name == "claude" else "Codex"
        style = "blue" if tool_name == "claude" else "green"
        conf_pct = int(decision.confidence * 100)
        llm_badge = "[dim]LLM[/dim]" if decision.used_llm else "[dim]heuristic[/dim]"

        self.console.print(
            f"\n  [{style}]⚡ {tool_label}[/{style}]"
            f"  [dim]{conf_pct}% conf  ·  {llm_badge}[/dim]\n"
            f"  [dim italic]{decision.reasoning}[/dim italic]\n"
        )

        # ── Execute ───────────────────────────────────────────────────────────
        profile = ProviderProfile(
            provider=Provider.CLAUDE if tool_name == "claude" else Provider.CODEX,
            mode=ProfileMode.LOCAL_APP,
            cli_command=tool_name,
        )
        self.executor.execute(
            __import__("saving_llm_budget.models", fromlist=["TaskRequest"]).TaskRequest(
                description=description,
                task_type=TaskType.FEATURE,
                scope=Scope.FEW_FILES,
                clarity=Clarity.SOMEWHAT_AMBIGUOUS,
                priority=Priority.BALANCED,
                auto_modify=True,
                allow_hybrid=self.config.allow_hybrid,
            ),
            profile,
        )

        # ── History ───────────────────────────────────────────────────────────
        self._history.append(
            {
                "description": description,
                "provider": tool_label,
                "confidence": decision.confidence,
                "executed": True,
            }
        )

    def _classify_with_spinner(self, description: str):
        """Call the classifier while showing a spinner."""
        result = None
        with Live(
            Spinner("dots", text=Text(" Analysing task...", style="cyan")),
            console=self.console,
            refresh_per_second=10,
            transient=True,
        ):
            result = self.service.classifier.classify(description)
        return result

    def _ask_override(self) -> bool:
        """Ask the user if they want to override the classification."""
        try:
            answer = input("Override classification? [y/N]: ").strip().lower()
            return answer in {"y", "yes"}
        except (EOFError, KeyboardInterrupt):
            return False

    def _interactive_override(self, classification) -> object:
        """Let the user interactively change individual classification fields."""
        from .services.classifier import ClassificationResult

        self.console.print("[bold]Override fields[/bold] (press Enter to keep current value):")

        def _pick(label: str, enum_cls, current):
            choices = [m.value for m in enum_cls]
            while True:
                raw = input(f"  {label} [{current.value}] ({', '.join(choices)}): ").strip()
                if not raw:
                    return current
                try:
                    return enum_cls(raw)
                except ValueError:
                    self.console.print(f"  [red]Invalid — choose from: {', '.join(choices)}[/red]")

        task_type = _pick("task_type", TaskType, classification.task_type)
        scope = _pick("scope", Scope, classification.scope)
        clarity = _pick("clarity", Clarity, classification.clarity)
        priority = _pick("priority", Priority, classification.priority)

        try:
            lc_raw = input(f"  long_context [{classification.long_context}] (true/false): ").strip()
            long_context = (lc_raw.lower() in {"true", "yes", "1"}) if lc_raw else classification.long_context
            am_raw = input(f"  auto_modify [{classification.auto_modify}] (true/false): ").strip()
            auto_modify = (am_raw.lower() in {"true", "yes", "1"}) if am_raw else classification.auto_modify
        except (EOFError, KeyboardInterrupt):
            long_context = classification.long_context
            auto_modify = classification.auto_modify

        return ClassificationResult(
            task_type=task_type,
            scope=scope,
            clarity=clarity,
            priority=priority,
            long_context=long_context,
            auto_modify=auto_modify,
            reasoning=classification.reasoning + " [manually overridden]",
            used_llm=classification.used_llm,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _profile_summary(self) -> Optional[str]:
        if not self.profile or not self.profile_name:
            return None
        mode_label = "API" if self.profile.mode.value == "api" else "local app"
        return f"{self.profile_name} → {self.profile.provider.value} via {mode_label}"
