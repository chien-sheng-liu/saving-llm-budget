"""Codex adapter skeleton."""

from __future__ import annotations

from .base import ProviderAdapter, ProviderExecutionResult, ProviderPlan
from ..models import Provider, TaskRequest


class CodexAdapter(ProviderAdapter):
    provider = Provider.CODEX

    def plan(self, task: TaskRequest) -> ProviderPlan:
        raise NotImplementedError("Codex planning not implemented in the MVP")

    def execute(self, task: TaskRequest, plan: ProviderPlan | None = None) -> ProviderExecutionResult:
        raise NotImplementedError("Codex execution not implemented in the MVP")
