"""Interactive chat session with automatic model routing."""

from __future__ import annotations

from typing import Optional

from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from . import __version__, constants
from .config import AppConfig
from .providers.claude import ClaudeChatAdapter
from .providers.openai_provider import OpenAIChatAdapter
from .services.model_selector import estimate_cost, select_model
from .services.recommender import RoutingService
from .models import Provider

_SYSTEM_PROMPT = (
    "You are a highly capable AI coding assistant. "
    "Answer concisely and accurately. "
    "When writing code, use proper formatting and explain your changes."
)

# ── Provider colours ──────────────────────────────────────────────────────────
_PROVIDER_STYLE = {
    "anthropic": "blue",
    "openai":    "green",
}

_PROVIDER_LABEL = {
    "anthropic": "Claude",
    "openai":    "OpenAI",
}


class ChatSession:
    """Auto-routing chat session that picks the best model for every prompt."""

    def __init__(
        self,
        anthropic_key: str = "",
        openai_key: str = "",
        config: Optional[AppConfig] = None,
    ) -> None:
        self.console = Console()
        self.anthropic_key = anthropic_key
        self.openai_key = openai_key
        self.config = config
        self.history: list[dict] = []
        self.total_cost: float = 0.0
        self.turn_count: int = 0
        self.last_model: str = ""
        self._service = RoutingService()
        self._claude = ClaudeChatAdapter(api_key=anthropic_key)
        self._openai = OpenAIChatAdapter(api_key=openai_key)

    # ── public entry point ────────────────────────────────────────────────────

    def run(self) -> None:
        self._print_welcome()
        try:
            while True:
                try:
                    prompt = self._read_input()
                except (EOFError, KeyboardInterrupt):
                    break

                prompt = prompt.strip()
                if not prompt:
                    continue

                if prompt.startswith("/"):
                    if self._handle_command(prompt):
                        break
                    continue

                self._process(prompt)
        finally:
            self._print_farewell()

    # ── welcome / farewell ────────────────────────────────────────────────────

    def _print_welcome(self) -> None:
        # Build provider status rows
        providers: list[str] = []
        if self.anthropic_key:
            providers.append(
                "[blue]● Claude[/blue]  [dim]Haiku · Sonnet · Opus[/dim]"
            )
        else:
            providers.append("[dim]○ Claude    (no ANTHROPIC_API_KEY)[/dim]")

        if self.openai_key:
            providers.append(
                "[green]● OpenAI[/green]  [dim]GPT-4o-mini · GPT-4o[/dim]"
            )
        else:
            providers.append("[dim]○ OpenAI    (no OPENAI_API_KEY)[/dim]")

        body = Text.assemble(
            ("slb chat", "bold cyan"),
            (f"  v{__version__}\n", "dim"),
            ("Automatically picks the best model for every prompt.\n\n", ""),
            *[(f"{p}\n", "") for p in providers],
            ("\n", ""),
            ("Type /help for commands  ·  Ctrl+C or /exit to quit", "dim"),
        )
        self.console.print(Panel(body, border_style="cyan", padding=(1, 3)))

    def _print_farewell(self) -> None:
        self.console.print()
        if self.turn_count == 0:
            self.console.print("[dim]No messages sent. Goodbye![/dim]")
            return

        table = Table.grid(padding=(0, 2))
        table.add_row("[dim]Turns[/dim]",       f"[bold]{self.turn_count}[/bold]")
        table.add_row("[dim]Total cost[/dim]",  f"[bold]${self.total_cost:.4f}[/bold]")
        if self.last_model:
            table.add_row("[dim]Last model[/dim]", f"[bold]{self.last_model}[/bold]")
        self.console.print(Panel(table, title="[dim]Session summary[/dim]", border_style="dim", padding=(0, 2)))

    # ── input ─────────────────────────────────────────────────────────────────

    def _read_input(self) -> str:
        self.console.print()
        self.console.print("[bold green]You[/bold green] [dim]›[/dim] ", end="")
        return input()

    # ── commands ──────────────────────────────────────────────────────────────

    def _handle_command(self, raw: str) -> bool:
        """Return True if the session should exit."""
        cmd = raw.lower().strip()

        if cmd in ("/exit", "/quit"):
            return True

        if cmd == "/clear":
            self.history.clear()
            self.console.print("[dim]  Conversation history cleared.[/dim]")

        elif cmd == "/cost":
            self.console.print(
                f"[dim]  Session cost: [bold]${self.total_cost:.4f}[/bold]"
                f"  across [bold]{self.turn_count}[/bold] turn(s)[/dim]"
            )

        elif cmd == "/model":
            if self.last_model:
                self.console.print(f"[dim]  Last model: [bold]{self.last_model}[/bold][/dim]")
            else:
                self.console.print("[dim]  No model used yet.[/dim]")

        elif cmd == "/status":
            self._print_status()

        elif cmd == "/help":
            self._print_help()

        else:
            self.console.print(
                f"[red]  Unknown command:[/red] [bold]{raw}[/bold]  "
                "[dim](type /help for available commands)[/dim]"
            )

        return False

    def _print_help(self) -> None:
        table = Table.grid(padding=(0, 3))
        table.add_row("[cyan]/clear[/cyan]",  "Clear conversation history")
        table.add_row("[cyan]/cost[/cyan]",   "Show session spend so far")
        table.add_row("[cyan]/model[/cyan]",  "Show last model used")
        table.add_row("[cyan]/status[/cyan]", "Show active providers and keys")
        table.add_row("[cyan]/help[/cyan]",   "Show this help")
        table.add_row("[cyan]/exit[/cyan]",   "Quit (also Ctrl+C)")
        self.console.print(Panel(table, title="[bold]Commands[/bold]", border_style="dim", padding=(0, 2)))

    def _print_status(self) -> None:
        table = Table.grid(padding=(0, 3))
        if self.anthropic_key:
            table.add_row("[blue]● Claude[/blue]",  "[green]active[/green]", "[dim]Haiku · Sonnet · Opus[/dim]")
        else:
            table.add_row("[dim]○ Claude[/dim]",    "[red]no key[/red]",     "[dim]set ANTHROPIC_API_KEY[/dim]")
        if self.openai_key:
            table.add_row("[green]● OpenAI[/green]", "[green]active[/green]", "[dim]GPT-4o-mini · GPT-4o[/dim]")
        else:
            table.add_row("[dim]○ OpenAI[/dim]",    "[red]no key[/red]",     "[dim]set OPENAI_API_KEY[/dim]")
        self.console.print(Panel(table, title="[bold]Provider status[/bold]", border_style="dim", padding=(0, 2)))

    # ── main processing loop ──────────────────────────────────────────────────

    def _process(self, prompt: str) -> None:
        # ── 1. Classify + route (with spinner) ───────────────────────────────
        try:
            with self.console.status("[dim]Routing…[/dim]", spinner="dots"):
                decision, classification = self._service.recommend_from_description(
                    prompt, config=self.config
                )
        except Exception as exc:
            self.console.print(f"[red]  Routing error: {exc}[/red]")
            return

        model_id, provider_name = select_model(decision, classification)
        self.last_model = model_id

        # Guard: check key availability before calling
        if provider_name == "anthropic" and not self.anthropic_key:
            # Fall back to OpenAI if available
            if self.openai_key:
                from . import constants as _c
                model_id = _c.OPENAI_STANDARD
                provider_name = "openai"
            else:
                self.console.print(
                    "[red]  No Anthropic API key.[/red]  "
                    "Restart with [bold]slb chat --anthropic-key ...[/bold] "
                    "or export [bold]ANTHROPIC_API_KEY[/bold]."
                )
                return

        if provider_name == "openai" and not self.openai_key:
            if self.anthropic_key:
                from . import constants as _c
                model_id = _c.CLAUDE_SONNET
                provider_name = "anthropic"
            else:
                self.console.print(
                    "[red]  No OpenAI API key.[/red]  "
                    "Restart with [bold]slb chat --openai-key ...[/bold] "
                    "or export [bold]OPENAI_API_KEY[/bold]."
                )
                return

        # ── 2. Show routing badge ─────────────────────────────────────────────
        style = _PROVIDER_STYLE[provider_name]
        label = _PROVIDER_LABEL[provider_name]
        confidence_pct = int(decision.confidence * 100)
        reasoning_short = classification.reasoning.split(".")[0]
        self.console.print(
            f"  [{style}]⚡ {model_id}[/{style}]"
            f"  [dim]{label}  ·  {confidence_pct}% conf  ·  {reasoning_short}[/dim]"
        )

        # ── 3. Add user turn to history ───────────────────────────────────────
        self.history.append({"role": "user", "content": prompt})

        # ── 4. Stream response ────────────────────────────────────────────────
        self.console.print()
        self.console.print(f"[bold]Assistant[/bold] [dim]({model_id})[/dim]")
        self.console.print()

        response_text = ""
        try:
            if provider_name == "anthropic":
                for chunk in self._claude.stream(model_id, self.history, system=_SYSTEM_PROMPT):
                    print(chunk, end="", flush=True)
                    response_text += chunk
                input_tok, output_tok = self._claude.last_usage
            else:
                for chunk in self._openai.stream(model_id, self.history, system=_SYSTEM_PROMPT):
                    print(chunk, end="", flush=True)
                    response_text += chunk
                input_tok, output_tok = self._openai.last_usage

            print()  # newline after streamed content
        except Exception as exc:
            self.console.print(f"\n[red]  API error:[/red] {exc}")
            self.history.pop()
            return

        # ── 5. Update state + show cost footer ───────────────────────────────
        self.history.append({"role": "assistant", "content": response_text})
        cost = estimate_cost(model_id, input_tok, output_tok)
        self.total_cost += cost
        self.turn_count += 1

        self.console.print(
            f"\n[dim]  ↳ {input_tok} in · {output_tok} out"
            f"  ·  ${cost:.4f} this turn"
            f"  ·  ${self.total_cost:.4f} session[/dim]"
        )
        self.console.print(Rule(style="dim"))
