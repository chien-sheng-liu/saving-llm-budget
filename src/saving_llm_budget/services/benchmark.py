"""Benchmark mode scaffolding."""

from __future__ import annotations

from ..models import BenchmarkReport, TaskRequest


class BenchmarkService:
    """Prepare benchmark metadata without actually running providers."""

    def prepare(self, task: TaskRequest) -> BenchmarkReport:
        return BenchmarkReport(
            enabled=True,
            notes=["Benchmark mode requested; awaiting provider adapters."],
            recommended_checks=[
                "Capture token usage per provider",
                "Compare plan vs. execution latency",
            ],
        )
