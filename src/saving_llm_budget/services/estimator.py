"""Lightweight heuristic estimations for complexity and cost."""

from __future__ import annotations

from typing import List

from ..models import (
    Clarity,
    ComplexityLevel,
    Estimation,
    Priority,
    Scope,
    TaskRequest,
    TaskType,
)


class Estimator:
    """Provide transparent estimates for token complexity and cost."""

    def estimate(self, task: TaskRequest) -> Estimation:
        notes: List[str] = []
        complexity_score = 1
        scope_boost = {
            Scope.SINGLE_FILE: 0,
            Scope.FEW_FILES: 1,
            Scope.MODULE: 2,
            Scope.REPO_WIDE: 3,
        }[task.scope]
        complexity_score += scope_boost
        if scope_boost:
            notes.append(f"Scope bump +{scope_boost}")

        clarity_penalty = {
            Clarity.VERY_CLEAR: 0,
            Clarity.SOMEWHAT_AMBIGUOUS: 1,
            Clarity.VERY_AMBIGUOUS: 2,
        }[task.clarity]
        complexity_score += clarity_penalty
        if clarity_penalty:
            notes.append(f"Ambiguity +{clarity_penalty}")

        if task.long_context:
            complexity_score += 1
            notes.append("Long context requirement +1")
        if task.task_type in {TaskType.ARCHITECTURE, TaskType.REFACTOR}:
            complexity_score += 1
            notes.append("Strategic task type +1")

        complexity = self._bucket(complexity_score)
        token_complexity = self._bucket(
            complexity_score - 1 if task.scope in {Scope.SINGLE_FILE, Scope.FEW_FILES} else complexity_score
        )

        cost_score = complexity_score
        if task.priority == Priority.CHEAPEST:
            cost_score -= 1
            notes.append("Cost priority -1")
        elif task.priority == Priority.BEST_QUALITY:
            cost_score += 1
            notes.append("Quality priority +1")
        if task.auto_modify:
            cost_score -= 0.5
            notes.append("Automation lowers iteration cost")

        cost_level = self._bucket(cost_score)
        return Estimation(
            complexity=complexity,
            token_complexity=token_complexity,
            cost_level=cost_level,
            notes=notes,
        )

    def _bucket(self, score: float) -> ComplexityLevel:
        if score <= 2:
            return ComplexityLevel.LOW
        if score <= 4:
            return ComplexityLevel.MEDIUM
        return ComplexityLevel.HIGH
