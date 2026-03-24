"""
Environment detection and tool installation wizard.

Checks whether Node.js, Claude Code, and Codex CLI are available,
and offers to install missing tools interactively.
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


# ── Tool metadata ──────────────────────────────────────────────────────────────

@dataclass
class ToolStatus:
    name: str
    installed: bool
    version: Optional[str] = None
    path: Optional[str] = None


TOOLS = {
    "claude": {
        "label":   "Claude Code",
        "package": "@anthropic-ai/claude-code",
        "check":   ["claude", "--version"],
        "docs":    "https://docs.anthropic.com/claude-code",
    },
    "codex": {
        "label":   "Codex CLI",
        "package": "@openai/codex",
        "check":   ["codex", "--version"],
        "docs":    "https://github.com/openai/codex",
    },
}


# ── Detection ──────────────────────────────────────────────────────────────────

def _get_version(cmd: list[str]) -> Optional[str]:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        output = (result.stdout + result.stderr).strip().splitlines()
        return output[0] if output else None
    except Exception:
        return None


def detect_node() -> ToolStatus:
    path = shutil.which("node")
    if not path:
        return ToolStatus("node", False)
    version = _get_version(["node", "--version"])
    return ToolStatus("node", True, version, path)


def detect_npm() -> ToolStatus:
    path = shutil.which("npm")
    if not path:
        return ToolStatus("npm", False)
    version = _get_version(["npm", "--version"])
    return ToolStatus("npm", True, version, path)


def detect_tool(tool_name: str) -> ToolStatus:
    info = TOOLS[tool_name]
    path = shutil.which(tool_name)
    if not path:
        return ToolStatus(info["label"], False)
    version = _get_version(info["check"])
    return ToolStatus(info["label"], True, version, path)


def detect_all() -> dict[str, ToolStatus]:
    return {
        "node":   detect_node(),
        "npm":    detect_npm(),
        "claude": detect_tool("claude"),
        "codex":  detect_tool("codex"),
    }


# ── Display ────────────────────────────────────────────────────────────────────

def print_environment_status(console: Console, statuses: dict[str, ToolStatus] | None = None) -> None:
    statuses = statuses or detect_all()

    table = Table.grid(padding=(0, 3))
    for key, status in statuses.items():
        if status.installed:
            icon = "[green]✓[/green]"
            detail = f"[dim]{status.version or ''}[/dim]"
        else:
            icon = "[red]✗[/red]"
            detail = "[dim]not found[/dim]"
        table.add_row(icon, f"[bold]{status.name}[/bold]", detail)

    console.print(Panel(table, title="[bold]Environment[/bold]", border_style="dim", padding=(0, 2)))


# ── Node installation hints ────────────────────────────────────────────────────

def _node_install_hint() -> str:
    os_name = platform.system()
    if os_name == "Darwin":
        return (
            "Install Node.js via Homebrew:\n"
            "  [bold]brew install node[/bold]\n\n"
            "Or download from: [link]https://nodejs.org[/link]"
        )
    if os_name == "Linux":
        return (
            "Install Node.js via your package manager:\n"
            "  [bold]sudo apt install nodejs npm[/bold]   [dim](Debian/Ubuntu)[/dim]\n"
            "  [bold]sudo dnf install nodejs npm[/bold]   [dim](Fedora)[/dim]\n\n"
            "Or use nvm: [link]https://github.com/nvm-sh/nvm[/link]"
        )
    # Windows
    return "Download Node.js from: [link]https://nodejs.org[/link]"


# ── Installation ───────────────────────────────────────────────────────────────

def install_tool(tool_name: str, console: Console) -> bool:
    """
    Install *tool_name* ("claude" or "codex") via npm.
    Returns True on success.
    """
    info = TOOLS[tool_name]
    package = info["package"]
    label = info["label"]

    # Check npm first
    if not shutil.which("npm"):
        console.print(
            Panel(
                f"[red]npm is required to install {label}.[/red]\n\n"
                + _node_install_hint(),
                title="Node.js not found",
                border_style="red",
                padding=(1, 3),
            )
        )
        return False

    console.print(f"\n[dim]  Running: npm install -g {package}[/dim]\n")

    try:
        with console.status(f"[dim]Installing {label}…[/dim]", spinner="dots"):
            result = subprocess.run(
                ["npm", "install", "-g", package],
                capture_output=True,
                text=True,
            )

        if result.returncode == 0:
            console.print(f"  [green]✓[/green] [bold]{label}[/bold] installed successfully.")
            return True
        else:
            error_lines = (result.stderr or result.stdout or "unknown error").strip()
            console.print(
                Panel(
                    f"[red]Installation failed.[/red]\n\n{error_lines}\n\n"
                    f"Try manually:\n  [bold]npm install -g {package}[/bold]\n"
                    f"Docs: {info['docs']}",
                    title=f"{label} installation failed",
                    border_style="red",
                    padding=(1, 3),
                )
            )
            return False

    except FileNotFoundError:
        console.print(f"[red]  npm not found in PATH.[/red]\n" + _node_install_hint())
        return False
    except KeyboardInterrupt:
        console.print("\n[yellow]  Installation cancelled.[/yellow]")
        return False


# ── ensure_tool: check + optionally install ────────────────────────────────────

def ensure_tool(
    tool_name: str,
    console: Console,
    auto_install: bool = True,
) -> bool:
    """
    Check if *tool_name* is installed. If not, offer to install it.
    Returns True if the tool is available after this call.
    """
    status = detect_tool(tool_name)
    if status.installed:
        return True

    info = TOOLS[tool_name]
    label = info["label"]

    console.print(
        f"\n  [yellow]○[/yellow] [bold]{label}[/bold] is not installed."
    )

    if not auto_install:
        console.print(
            f"  Install it with: [bold]npm install -g {info['package']}[/bold]\n"
            f"  Docs: {info['docs']}"
        )
        return False

    try:
        confirmed = typer.confirm(f"  Install {label} now?", default=True)
    except (EOFError, KeyboardInterrupt):
        confirmed = False

    if not confirmed:
        console.print(f"  [dim]Skipped. Install later: npm install -g {info['package']}[/dim]")
        return False

    return install_tool(tool_name, console)


# ── Full setup wizard ──────────────────────────────────────────────────────────

def run_setup_wizard(console: Console) -> dict[str, bool]:
    """
    Interactive wizard that checks the full environment and offers to install
    missing tools. Returns a dict of {tool_name: is_available}.
    """
    console.print(
        Panel(
            Text.assemble(
                ("slb setup\n", "bold cyan"),
                ("Checks your environment and installs the tools slb dispatches to.\n\n", ""),
                ("Required: ", "bold"),
                ("Node.js + npm\n", ""),
                ("Optional: ", "bold"),
                ("Claude Code  (for Claude-routed tasks)\n", ""),
                ("            ", ""),
                ("Codex CLI    (for OpenAI-routed tasks)", ""),
            ),
            border_style="cyan",
            padding=(1, 3),
        )
    )

    console.print()
    statuses = detect_all()
    print_environment_status(console, statuses)

    results: dict[str, bool] = {}

    # ── Node.js / npm ──────────────────────────────────────────────────────────
    if not statuses["node"].installed or not statuses["npm"].installed:
        console.print(
            Panel(
                "[red]Node.js and npm are required.[/red]\n\n"
                + _node_install_hint(),
                title="Node.js not found",
                border_style="red",
                padding=(1, 3),
            )
        )
        console.print("[dim]  Re-run [bold]slb setup[/bold] after installing Node.js.[/dim]")
        return {"claude": False, "codex": False}

    # ── Claude Code ────────────────────────────────────────────────────────────
    console.print()
    if statuses["claude"].installed:
        console.print(
            f"  [green]✓[/green] [bold]Claude Code[/bold]  "
            f"[dim]{statuses['claude'].version or ''}[/dim]"
        )
        results["claude"] = True
    else:
        results["claude"] = ensure_tool("claude", console)

    # ── Codex ──────────────────────────────────────────────────────────────────
    console.print()
    if statuses["codex"].installed:
        console.print(
            f"  [green]✓[/green] [bold]Codex CLI[/bold]  "
            f"[dim]{statuses['codex'].version or ''}[/dim]"
        )
        results["codex"] = True
    else:
        results["codex"] = ensure_tool("codex", console)

    # ── Summary ────────────────────────────────────────────────────────────────
    console.print()
    available = [k for k, v in results.items() if v]
    if available:
        tools_str = "  and  ".join(f"[bold]{t}[/bold]" for t in available)
        console.print(
            Panel(
                f"Ready! slb will dispatch tasks to {tools_str}.\n\n"
                "Start with: [bold cyan]slb do \"your task here\"[/bold cyan]",
                border_style="green",
                padding=(0, 2),
            )
        )
    else:
        console.print(
            Panel(
                "[yellow]No CLI tools available.[/yellow]\n\n"
                "slb will fall back to direct API calls via [bold]slb chat[/bold].",
                border_style="yellow",
                padding=(0, 2),
            )
        )

    return results
