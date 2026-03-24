from io import StringIO

from rich.console import Console

from saving_llm_budget.config import ProviderProfile
from saving_llm_budget.models import ProfileMode, Provider, TaskRequest, TaskType, Scope, Clarity, Priority
from saving_llm_budget.providers.executor import ProviderExecutor


def sample_task() -> TaskRequest:
    return TaskRequest(
        description="demo",
        task_type=TaskType.FEATURE,
        scope=Scope.FEW_FILES,
        clarity=Clarity.VERY_CLEAR,
        priority=Priority.BALANCED,
        long_context=False,
        auto_modify=False,
        allow_hybrid=True,
    )


def test_executor_api_mode_prints_placeholder(monkeypatch):
    buffer = StringIO()
    console = Console(file=buffer, width=80, force_terminal=False, color_system=None)
    executor = ProviderExecutor(console)
    profile = ProviderProfile(provider=Provider.CLAUDE, mode=ProfileMode.API, api_keys=["ANTHROPIC_API_KEY"])
    executor.execute(sample_task(), profile)
    output = buffer.getvalue()
    # Title text changed to "API mode (direct call)"
    assert "API mode" in output
    assert "ANTHROPIC_API_KEY" in output


def test_executor_cli_mode_runs_command(monkeypatch):
    import subprocess

    buffer = StringIO()
    console = Console(file=buffer, width=80, force_terminal=False, color_system=None)
    executor = ProviderExecutor(console)
    profile = ProviderProfile(provider=Provider.CODEX, mode=ProfileMode.LOCAL_APP, cli_command="echo")

    called = {}

    class FakeCompletedProcess:
        returncode = 0

    def fake_run(cmd, **kwargs):
        called["cmd"] = cmd
        return FakeCompletedProcess()

    monkeypatch.setattr("shutil.which", lambda x: f"/usr/bin/{x}")
    monkeypatch.setattr("subprocess.run", fake_run)
    executor.execute(sample_task(), profile)
    assert called["cmd"][0] == "echo"
    # For Codex, the prompt is passed as the last argument
    assert "demo" in called["cmd"][-1]
