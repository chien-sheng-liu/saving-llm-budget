"""Utilities to execute tasks with selected providers."""

from __future__ import annotations

import shlex
import shutil
import subprocess
import sys
from textwrap import dedent

from rich.console import Console
from rich.panel import Panel

from ..config import ProviderProfile
from ..models import ProfileMode, Provider, TaskRequest


def _build_prompt(task: TaskRequest) -> str:
    """Build a clear natural-language prompt to pass to the CLI tool."""
    lines = [task.description]
    details = []
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


class ProviderExecutor:
    """Execute tasks via provider CLI tools with real-time streaming output."""

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()

    def execute(self, task: TaskRequest, profile: ProviderProfile) -> None:
        if profile.mode == ProfileMode.API:
            self._show_api_placeholder(task, profile)
            return
        self._run_cli_command(task, profile)

    def _show_api_placeholder(self, task: TaskRequest, profile: ProviderProfile) -> None:
        envs = profile.api_keys or ["API_KEY"]
        message = dedent(
            f"""
            Provider: {profile.provider.value}
            Mode: API call
            Expected environment variables: {', '.join(envs)}

            (Future release will call the real API. For now, run this task via your normal workflow.)

            Task → {task.description}
            Type → {task.task_type.value}, Scope → {task.scope.value}, Priority → {task.priority.value}
            """
        ).strip()
        self.console.print(Panel(message, title="API execution placeholder", expand=False))

    def _run_cli_command(self, task: TaskRequest, profile: ProviderProfile) -> None:
        if not profile.cli_command:
            self.console.print(
                Panel(
                    "No CLI command configured for this profile.\n"
                    "Edit the profile or run `saving-llm-budget profile add`.",
                    title="Missing CLI command",
                    style="red",
                )
            )
            return

        base_cmd = shlex.split(profile.cli_command)
        executable = base_cmd[0]

        # Check the executable exists before trying to run it
        if not shutil.which(executable):
            install_hint = _install_hint(profile.provider, executable)
            self.console.print(
                Panel(
                    f"Executable '{executable}' not found in PATH.\n\n{install_hint}",
                    title="CLI not found",
                    style="red",
                )
            )
            return

        prompt = _build_prompt(task)
        command = _build_command(base_cmd, profile.provider, prompt)

        self.console.print(
            Panel(
                f"Command: [bold]{' '.join(command[:2])} ...[/bold]\n"
                f"Provider: {profile.provider.value}  |  Mode: local app\n"
                "Streaming output below — press Ctrl+C to abort.",
                title=f"Executing via {profile.provider.value}",
                border_style="green",
            )
        )
        self.console.rule()

        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            assert process.stdout is not None
            for line in process.stdout:
                self.console.print(line, end="")
            process.wait()
            self.console.rule()
            if process.returncode != 0:
                self.console.print(
                    f"[yellow]Process exited with code {process.returncode}.[/yellow]"
                )
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Interrupted — returning to prompt.[/yellow]")
            try:
                process.terminate()
            except Exception:  # noqa: BLE001
                pass
        except FileNotFoundError:
            self.console.print(
                Panel(
                    f"Could not launch '{executable}'.",
                    style="red",
                    title="CLI command failed",
                )
            )


def _build_command(base_cmd: list[str], provider: Provider, prompt: str) -> list[str]:
    """Build the final argument list for the provider CLI."""
    if provider == Provider.CLAUDE:
        # `claude --print "prompt"` runs non-interactively and streams output
        return [*base_cmd, "--print", prompt]
    elif provider == Provider.CODEX:
        # `codex "prompt"` is the standard invocation
        return [*base_cmd, prompt]
    else:
        # Hybrid or unknown — fall back to piping via print flag if possible
        return [*base_cmd, "--print", prompt]


def _install_hint(provider: Provider, executable: str) -> str:
    hints = {
        Provider.CLAUDE: "Install Claude Code: https://docs.anthropic.com/claude-code\n  npm install -g @anthropic-ai/claude-code",
        Provider.CODEX: "Install Codex CLI: https://github.com/openai/codex\n  npm install -g @openai/codex",
    }
    return hints.get(provider, f"Install '{executable}' and ensure it is in your PATH.")
