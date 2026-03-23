"""Local test runner helper used by the CLI."""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from typing import Iterable, Sequence

from rich.console import Console
from rich.panel import Panel


@dataclass
class TestResult:
    success: bool
    return_code: int
    duration: float
    command: Sequence[str]
    stdout: str
    stderr: str


class TestRunner:
    """Execute pytest with a friendly Rich interface."""

    __test__ = False  # prevent pytest from collecting this class

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()

    def run(self, args: Iterable[str] = ()) -> TestResult:
        command = ["python", "-m", "pytest", *list(args)]
        self.console.print(Panel("Running local tests", subtitle=" ".join(command)))
        start = time.perf_counter()
        try:
            proc = subprocess.run(
                command,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as exc:  # pragma: no cover - defensive
            raise RuntimeError("Python executable not found while running tests.") from exc
        duration = time.perf_counter() - start
        result = TestResult(
            success=proc.returncode == 0,
            return_code=proc.returncode,
            duration=duration,
            command=command,
            stdout=proc.stdout,
            stderr=proc.stderr,
        )
        if "No module named pytest" in result.stderr:
            hint = (
                "pytest is not installed in this environment. Install it via"
                " `pip install -e .[dev]` or `pip install pytest`."
            )
            raise RuntimeError(hint)
        return result
