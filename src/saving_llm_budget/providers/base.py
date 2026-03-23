"""Abstract provider adapter definitions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

from ..models import Provider, TaskRequest


@dataclass
class ProviderPlan:
    """Lightweight description of how a provider should approach a task."""

    summary: str
    steps: List[str]


@dataclass
class ProviderExecutionResult:
    """Placeholder for provider execution results."""

    provider: Provider
    output_snippet: Optional[str] = None
    tokens_consumed: Optional[int] = None
    notes: List[str] | None = None


class ProviderAdapter(ABC):
    """Base adapter that future integrations must extend."""

    provider: Provider

    @abstractmethod
    def plan(self, task: TaskRequest) -> ProviderPlan:
        """Return a high-level plan for the task."""

    @abstractmethod
    def execute(self, task: TaskRequest, plan: ProviderPlan | None = None) -> ProviderExecutionResult:
        """Execute the task using the provider."""
