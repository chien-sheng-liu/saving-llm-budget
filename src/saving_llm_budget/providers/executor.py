"""Dispatch tasks to provider CLI tools (Claude Code, Codex)."""

from __future__ import annotations

import shlex
import subprocess
from textwrap import dedent

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

from ..config import ProviderProfile
from ..models import ProfileMode, Provider, TaskRequest


def _build_prompt(task: TaskRequest) -> str:
    """Build a natural-language prompt to pass to the CLI tool."""
    lines = [task.description]
    details: list[str] = []
    if task.task_type:
        details.append(f"Task type: {task.task_type.value}")
    if task.scope:
        details.append(f"Scope: {task.scope.value}")
    if task.long_context:
        details.append("Long context required.")
    if task.auto_modify:
        details.append("Automated file modifications are allowed.")
    if task.repo_path:
        details.append(f"Repository: {task.repo_path}")
    if details:
        lines.append("")
        lines.extend(details)
    return "\n".join(lines)


def _build_command(base_cmd: list[str], provider: Provider, prompt: str) -> list[str]:
    """Build the final argument list for the provider CLI."""
    if provider == Provider.CODEX:
        # codex "prompt"
        return [*base_cmd, prompt]
    # Claude Code and Hybrid: interactive mode (no --print so the full TUI runs)
    return [*base_cmd, prompt]


def _install_hint(provider: Provider) -> str:
    hints = {
        Provider.CLAUDE: (
            "Install Claude Code:\n"
            "  [bold]npm install -g @anthropic-ai/claude-code[/bold]\n"
            "  Docs: https://docs.anthropic.com/claude-code\n\n"
            "Or run [bold]slb setup[/bold] to install automatically."
        ),
        Provider.CODEX: (
            "Install Codex CLI:\n"
            "  [bold]npm install -g @openai/codex[/bold]\n"
            "  Docs: https://github.com/openai/codex\n\n"
            "Or run [bold]slb setup[/bold] to install automatically."
        ),
    }
    return hints.get(provider, "Run [bold]slb setup[/bold] to install required tools.")


class ProviderExecutor:
    """Dispatch tasks to provider CLI tools with full terminal (TTY) handoff."""

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()

    def execute(self, task: TaskRequest, profile: ProviderProfile) -> int:
        """
        Execute *task* via the given *profile*.
        Returns the exit code (0 = success).
        """
        if profile.mode == ProfileMode.API:
            self._show_api_placeholder(task, profile)
            return 0
        return self._dispatch_cli(task, profile)

    # ── API placeholder ────────────────────────────────────────────────────────

    def _show_api_placeholder(self, task: TaskRequest, profile: ProviderProfile) -> None:
        envs = profile.api_keys or ["API_KEY"]
        message = dedent(
            f"""
            Provider : {profile.provider.value}
            Mode     : API call
            Env vars : {', '.join(envs)}

            Task  → {task.description}
            Type  → {task.task_type.value}
            Scope → {task.scope.value}
            """
        ).strip()
        self.console.print(Panel(message, title="API mode (direct call)", expand=False))

    # ── CLI dispatch ───────────────────────────────────────────────────────────

    def _dispatch_cli(self, task: TaskRequest, profile: ProviderProfile) -> int:
        import shutil

        if not profile.cli_command:
            self.console.print(
                Panel(
                    "No CLI command configured for this profile.\n"
                    "Run [bold]slb setup[/bold] or [bold]slb profile add[/bold].",
                    title="Missing CLI command",
                    border_style="red",
                )
            )
            return 1

        base_cmd = shlex.split(profile.cli_command)
        executable = base_cmd[0]

        if not shutil.which(executable):
            self.console.print(
                Panel(
                    f"[red]'{executable}' not found in PATH.[/red]\n\n"
                    + _install_hint(profile.provider),
                    title="CLI not installed",
                    border_style="red",
                    padding=(1, 3),
                )
            )
            return 1

        prompt = _build_prompt(task)
        command = _build_command(base_cmd, profile.provider, prompt)

        self.console.print(
            Panel(
                f"Provider : [bold]{profile.provider.value}[/bold]\n"
                f"Command  : [bold]{executable}[/bold]\n\n"
                "[dim]Ctrl+C to abort[/dim]",
                title=f"Dispatching to {profile.provider.value}",
                border_style="green",
                padding=(0, 2),
            )
        )
        self.console.print(Rule(style="dim"))

        try:
            # ── Full TTY handoff ───────────────────────────────────────────────
            # Do NOT use stdout=PIPE — that strips the TTY and breaks interactive
            # tools (colours, approval prompts, cursor movement all fail).
            # subprocess.run() with no redirection inherits stdin/stdout/stderr.
            result = subprocess.run(command)
            self.console.print(Rule(style="dim"))
            if result.returncode != 0:
                self.console.print(
                    f"[yellow]  Exited with code {result.returncode}.[/yellow]"
                )
            return result.returncode

        except KeyboardInterrupt:
            self.console.print("\n[yellow]  Interrupted.[/yellow]")
            return 130  # standard SIGINT exit code

        except FileNotFoundError:
            self.console.print(
                Panel(
                    f"[red]Could not launch '{executable}'.[/red]\n\n"
                    + _install_hint(profile.provider),
                    border_style="red",
                )
            )
            return 1
