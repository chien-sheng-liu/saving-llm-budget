"""Claude adapter skeleton."""

from __future__ import annotations

from .base import ProviderAdapter, ProviderExecutionResult, ProviderPlan
from ..models import Provider, TaskRequest


class ClaudeAdapter(ProviderAdapter):
    provider = Provider.CLAUDE

    def plan(self, task: TaskRequest) -> ProviderPlan:
        raise NotImplementedError("Claude planning not implemented in the MVP")

    def execute(self, task: TaskRequest, plan: ProviderPlan | None = None) -> ProviderExecutionResult:
        raise NotImplementedError("Claude execution not implemented in the MVP")
