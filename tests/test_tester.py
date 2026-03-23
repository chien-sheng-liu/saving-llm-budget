from io import StringIO

from rich.console import Console

from saving_llm_budget.services.tester import TestRunner


def test_test_runner_builds_command(monkeypatch):
    recorded = {}

    class DummyResult:
        returncode = 0
        stdout = "ok"
        stderr = ""

    def fake_run(cmd, capture_output, text):
        recorded["cmd"] = cmd
        assert capture_output is True
        assert text is True
        return DummyResult()

    monkeypatch.setattr("subprocess.run", fake_run)
    runner = TestRunner(console=Console(file=StringIO()))
    result = runner.run(["tests/test_router_engine.py"])
    assert recorded["cmd"] == ["python", "-m", "pytest", "tests/test_router_engine.py"]
    assert result.success is True
    assert result.stdout == "ok"
