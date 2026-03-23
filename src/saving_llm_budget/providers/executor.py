"""Utilities to execute tasks with selected providers."""

from __future__ import annotations

import shlex
import subprocess
from textwrap import dedent

from rich.console import Console
from rich.panel import Panel

from ..config import ProviderProfile
from ..models import ProfileMode, TaskRequest


class ProviderExecutor:
    """Provide lightweight hooks for API or CLI execution."""

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()

    def execute(self, task: TaskRequest, profile: ProviderProfile) -> None:
        if profile.mode == ProfileMode.API:
            self._simulate_api_call(task, profile)
            return
        self._run_cli_command(task, profile)

    def _simulate_api_call(self, task: TaskRequest, profile: ProviderProfile) -> None:
        envs = profile.api_keys or ["API_KEY"]
        message = dedent(
            f"""
            Provider: {profile.provider.value}
            Mode: API call
            Expected environment variables: {', '.join(envs)}

            (Future release will call the real API. For now, run this task via your normal workflow
            and consider copying the following description manually.)

            Task -> {task.description}
            Type -> {task.task_type.value}, Scope -> {task.scope.value}, Priority -> {task.priority.value}
            """
        ).strip()
        self.console.print(Panel(message, title="API execution placeholder", expand=False))

    def _run_cli_command(self, task: TaskRequest, profile: ProviderProfile) -> None:
        if not profile.cli_command:
            self.console.print(
                Panel(
                    "No CLI command configured for this profile. Edit the profile or set one via"
                    " `saving-llm-budget profile add`.",
                    title="Missing CLI command",
                    style="red",
                )
            )
            return
        command = shlex.split(profile.cli_command)
        payload = dedent(
            f"""
            Task: {task.description}
            Type: {task.task_type.value}
            Scope: {task.scope.value}
            Clarity: {task.clarity.value}
            Priority: {task.priority.value}
            Long context: {task.long_context}
            Auto modify: {task.auto_modify}
            """
        )
        self.console.print(
            Panel(
                f"Launching CLI command: {' '.join(command)}\nPayload sent via STDIN.",
                title=f"Executing with {profile.provider.value}",
            )
        )
        try:
            subprocess.run(command, input=payload, text=True, check=False)
        except FileNotFoundError:
            self.console.print(
                Panel(
                    f"Executable '{command[0]}' not found. Update the CLI command within the profile.",
                    style="red",
                    title="CLI command failed",
                )
            )
