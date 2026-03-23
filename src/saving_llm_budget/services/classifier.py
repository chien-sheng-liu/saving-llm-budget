"""LLM-powered task classifier that converts free-text descriptions into structured TaskRequest fields."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Optional

from .. import constants
from ..models import Clarity, Priority, Scope, TaskType


_SYSTEM_PROMPT = """\
You are a task classifier for an AI coding router. Given a natural language description of a coding task,
extract structured metadata. Respond ONLY with a valid JSON object — no prose, no markdown fences.

Fields to extract:
- task_type: one of bugfix, refactor, feature, architecture, explain, test, docs, review
- scope: one of single_file, few_files, module, repo_wide
- clarity: one of very_clear, somewhat_ambiguous, very_ambiguous
- priority: one of cheapest, balanced, best_quality
- long_context: true if the task needs to read many files or long outputs, false otherwise
- auto_modify: true if the task requires automated file modifications, false otherwise
- reasoning: 1-2 sentences explaining why you classified it this way

Examples:
Input: "Fix the null pointer exception in UserService.java line 42"
Output: {"task_type":"bugfix","scope":"single_file","clarity":"very_clear","priority":"cheapest","long_context":false,"auto_modify":true,"reasoning":"Single targeted bugfix in a specific file with clear description."}

Input: "Refactor the entire authentication module to use JWT and improve error handling across all services"
Output: {"task_type":"refactor","scope":"module","clarity":"somewhat_ambiguous","priority":"balanced","long_context":true,"auto_modify":true,"reasoning":"Module-level refactor touching multiple files; JWT change implies understanding across services."}

Input: "I'm not sure why the tests keep failing, can you investigate?"
Output: {"task_type":"bugfix","scope":"few_files","clarity":"very_ambiguous","priority":"balanced","long_context":false,"auto_modify":false,"reasoning":"Very vague description with no specific location; investigative nature suggests ambiguity."}
"""


@dataclass
class ClassificationResult:
    task_type: TaskType
    scope: Scope
    clarity: Clarity
    priority: Priority
    long_context: bool
    auto_modify: bool
    reasoning: str
    used_llm: bool = True


def _safe_enum(enum_cls, value: str, default):
    """Parse an enum value safely, falling back to default."""
    try:
        return enum_cls(value)
    except ValueError:
        return default


def _parse_response(raw: str) -> dict:
    """Extract JSON from the LLM response, stripping any accidental markdown."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return json.loads(text)


class TaskClassifier:
    """Classify a natural language task description using Claude Haiku."""

    def classify(self, description: str) -> ClassificationResult:
        """
        Classify *description* into structured fields.

        Falls back to sensible defaults if the API key is missing or the call fails.
        """
        api_key = os.getenv(constants.ANTHROPIC_API_KEY_VAR)
        if not api_key:
            return self._fallback(description, reason="no API key")

        try:
            import anthropic  # type: ignore

            client = anthropic.Anthropic(api_key=api_key)
            message = client.messages.create(
                model=constants.CLASSIFIER_MODEL,
                max_tokens=constants.CLASSIFIER_MAX_TOKENS,
                temperature=constants.CLASSIFIER_TEMPERATURE,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": description}],
            )
            raw = message.content[0].text
            data = _parse_response(raw)
            return ClassificationResult(
                task_type=_safe_enum(TaskType, data.get("task_type", ""), TaskType.FEATURE),
                scope=_safe_enum(Scope, data.get("scope", ""), Scope.FEW_FILES),
                clarity=_safe_enum(Clarity, data.get("clarity", ""), Clarity.SOMEWHAT_AMBIGUOUS),
                priority=_safe_enum(Priority, data.get("priority", ""), Priority.BALANCED),
                long_context=bool(data.get("long_context", False)),
                auto_modify=bool(data.get("auto_modify", False)),
                reasoning=str(data.get("reasoning", "LLM classification.")),
                used_llm=True,
            )
        except Exception:  # noqa: BLE001
            return self._fallback(description, reason="API error")

    def _fallback(self, description: str, reason: str) -> ClassificationResult:
        """Return conservative defaults when LLM classification is unavailable."""
        desc_lower = description.lower()

        # Simple heuristics when LLM is unavailable
        if any(w in desc_lower for w in ("fix", "bug", "error", "crash", "fail")):
            task_type = TaskType.BUGFIX
        elif any(w in desc_lower for w in ("refactor", "clean", "restructure", "move")):
            task_type = TaskType.REFACTOR
        elif any(w in desc_lower for w in ("test", "spec", "coverage")):
            task_type = TaskType.TEST
        elif any(w in desc_lower for w in ("explain", "why", "how does", "what is")):
            task_type = TaskType.EXPLAIN
        elif any(w in desc_lower for w in ("doc", "readme", "comment")):
            task_type = TaskType.DOCS
        else:
            task_type = TaskType.FEATURE

        scope = Scope.FEW_FILES
        if any(w in desc_lower for w in ("entire", "all", "whole", "repo", "project")):
            scope = Scope.REPO_WIDE
        elif any(w in desc_lower for w in ("file", "class", "function", "line")):
            scope = Scope.SINGLE_FILE

        return ClassificationResult(
            task_type=task_type,
            scope=scope,
            clarity=Clarity.SOMEWHAT_AMBIGUOUS,
            priority=Priority.BALANCED,
            long_context=False,
            auto_modify=False,
            reasoning=f"Heuristic classification ({reason} — set ANTHROPIC_API_KEY for LLM-powered routing).",
            used_llm=False,
        )
