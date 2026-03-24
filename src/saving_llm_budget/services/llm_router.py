"""
LLM-based routing: asks Claude Haiku which tool to use for a given task.
Replaces the rule-based scoring engine for slb do / slb chat dispatch.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Optional

from .. import constants
from ..services.model_selector import estimate_cost


_ROUTER_SYSTEM = """\
You are a routing agent for a developer CLI that dispatches coding tasks to one of two tools:

• Claude Code  — a local CLI tool powered by Claude (Anthropic)
• Codex        — a local CLI tool powered by GPT-4o (OpenAI)

Choose the BEST tool for the task. Guidelines:

Claude Code is better for:
  - Architecture decisions, system design, large refactors
  - Ambiguous or exploratory tasks ("I'm not sure why…", "Help me think through…")
  - Code review, explanation, deep reasoning
  - Tasks touching many files or requiring holistic understanding
  - Long, complex outputs

Codex is better for:
  - Clear, targeted bugfixes with a specific location
  - Writing or updating tests and documentation
  - Small, mechanical, well-defined changes
  - Cost-sensitive or high-frequency tasks

Respond with ONLY a JSON object — no prose, no markdown fences:
{"tool": "claude" | "codex", "reasoning": "<one sentence>", "confidence": 0.0–1.0}
"""


@dataclass
class LLMRoutingDecision:
    tool: str                 # "claude" or "codex"
    reasoning: str
    confidence: float
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    used_llm: bool = True


@dataclass
class SessionCost:
    """Accumulates token usage and cost across multiple routing calls."""
    routing_input_tokens: int = 0
    routing_output_tokens: int = 0
    routing_cost_usd: float = 0.0
    calls: int = 0

    def add(self, decision: LLMRoutingDecision) -> None:
        self.routing_input_tokens += decision.input_tokens
        self.routing_output_tokens += decision.output_tokens
        self.routing_cost_usd += decision.cost_usd
        self.calls += 1

    def summary(self) -> str:
        return (
            f"{self.calls} routing call(s)  ·  "
            f"{self.routing_input_tokens} in / {self.routing_output_tokens} out tokens  ·  "
            f"${self.routing_cost_usd:.5f} routing cost"
        )


class LLMRouter:
    """Route a task to claude or codex using Claude Haiku."""

    def __init__(self, api_key: str = "") -> None:
        self._api_key = api_key or os.getenv(constants.ANTHROPIC_API_KEY_VAR, "")

    def route(self, task: str) -> LLMRoutingDecision:
        """Return routing decision for *task*. Falls back to heuristics if no API key."""
        if not self._api_key:
            return self._heuristic_fallback(task)

        try:
            import anthropic

            client = anthropic.Anthropic(api_key=self._api_key)
            msg = client.messages.create(
                model=constants.CLASSIFIER_MODEL,
                max_tokens=128,
                temperature=0.0,
                system=_ROUTER_SYSTEM,
                messages=[{"role": "user", "content": task}],
            )
            raw = msg.content[0].text.strip()
            # Strip accidental markdown fences
            if raw.startswith("```"):
                lines = raw.splitlines()
                raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            data = json.loads(raw)

            tool = data.get("tool", "claude")
            if tool not in ("claude", "codex"):
                tool = "claude"

            in_tok  = msg.usage.input_tokens
            out_tok = msg.usage.output_tokens
            cost    = estimate_cost(constants.CLASSIFIER_MODEL, in_tok, out_tok)

            return LLMRoutingDecision(
                tool=tool,
                reasoning=str(data.get("reasoning", "")),
                confidence=float(data.get("confidence", 0.8)),
                input_tokens=in_tok,
                output_tokens=out_tok,
                cost_usd=cost,
                used_llm=True,
            )

        except Exception:  # noqa: BLE001 — any failure falls back gracefully
            return self._heuristic_fallback(task)

    # ── heuristic fallback (no API key or error) ──────────────────────────────

    def _heuristic_fallback(self, task: str) -> LLMRoutingDecision:
        desc = task.lower()
        if any(w in desc for w in ("architect", "design", "refactor", "review", "explain",
                                   "why", "understand", "ambiguous", "think", "help me")):
            tool, reasoning = "claude", "Exploratory or architectural task — Claude Code handles ambiguity better."
        elif any(w in desc for w in ("fix", "bug", "test", "doc", "comment", "typo",
                                     "rename", "format", "lint", "add line")):
            tool, reasoning = "codex", "Clear, targeted change — Codex is faster and cheaper."
        else:
            tool, reasoning = "claude", "Defaulting to Claude Code for balanced tasks."

        return LLMRoutingDecision(
            tool=tool,
            reasoning=reasoning + " (heuristic — set ANTHROPIC_API_KEY for LLM routing)",
            confidence=0.6,
            used_llm=False,
        )
