"""Tests for the REPL session."""

from __future__ import annotations

from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

from rich.console import Console

from saving_llm_budget.config import AppConfig, ProviderProfile
from saving_llm_budget.models import (
    Clarity,
    ComplexityLevel,
    Estimation,
    Priority,
    ProfileMode,
    Provider,
    ProviderScore,
    RoutingDecision,
    Scope,
    TaskType,
    Workflow,
)
from saving_llm_budget.repl import ReplSession
from saving_llm_budget.services.classifier import ClassificationResult


def _make_config() -> AppConfig:
    return AppConfig(default_mode="balanced", allow_hybrid=True, max_budget_usd=50.0)


def _make_profile() -> ProviderProfile:
    return ProviderProfile(provider=Provider.CLAUDE, mode=ProfileMode.LOCAL_APP, cli_command="claude")


def _make_decision() -> RoutingDecision:
    return RoutingDecision(
        provider=Provider.CLAUDE,
        workflow=Workflow.DIRECT_CLAUDE,
        confidence=0.85,
        reasoning="Good fit.",
        estimation=Estimation(
            complexity=ComplexityLevel.LOW,
            cost_level=ComplexityLevel.LOW,
            token_complexity=ComplexityLevel.LOW,
        ),
        scores=[ProviderScore(provider=Provider.CLAUDE, score=8.0, contributions=["test"])],
        suggested_action="Run directly.",
        cost_note="Low cost.",
    )


def _make_classification() -> ClassificationResult:
    return ClassificationResult(
        task_type=TaskType.FEATURE,
        scope=Scope.FEW_FILES,
        clarity=Clarity.VERY_CLEAR,
        priority=Priority.BALANCED,
        long_context=False,
        auto_modify=False,
        reasoning="Test classification.",
        used_llm=False,
    )


def _make_session(profile=None) -> tuple[ReplSession, Console, StringIO]:
    buffer = StringIO()
    console = Console(file=buffer, width=120, force_terminal=False, color_system=None)
    service = MagicMock()
    service.classifier = MagicMock()
    service.classifier.classify.return_value = _make_classification()
    service.recommend.return_value = _make_decision()
    service.recommend_from_description.return_value = (_make_decision(), _make_classification())
    executor = MagicMock()
    session = ReplSession(
        config=_make_config(),
        profile_name="test-profile" if profile else None,
        profile=profile or _make_profile(),
        service=service,
        executor=executor,
        console=console,
    )
    return session, console, buffer


# ---------------------------------------------------------------------------
# Command handling
# ---------------------------------------------------------------------------


def test_help_command_prints_help():
    session, _, buffer = _make_session()
    session._handle_command("/help")
    assert "Available commands" in buffer.getvalue()


def test_unknown_command_shows_error():
    session, _, buffer = _make_session()
    session._handle_command("/unknown_cmd")
    assert "Unknown command" in buffer.getvalue()


def test_profile_command_shows_profile():
    session, _, buffer = _make_session(profile=_make_profile())
    session._handle_command("/profile")
    output = buffer.getvalue()
    assert "Claude" in output or "claude" in output


def test_history_empty():
    session, _, buffer = _make_session()
    session._handle_command("/history")
    assert "No tasks" in buffer.getvalue()


def test_history_shows_entries():
    session, _, buffer = _make_session()
    session._history = [
        {"description": "fix bug", "provider": "Claude", "confidence": 0.9, "executed": True}
    ]
    session._handle_command("/history")
    assert "fix bug" in buffer.getvalue()


# ---------------------------------------------------------------------------
# Task flow
# ---------------------------------------------------------------------------


def test_classify_with_spinner_calls_classifier():
    session, _, _ = _make_session()
    result = session._classify_with_spinner("fix the bug")
    session.service.classifier.classify.assert_called_once_with("fix the bug")
    assert result.task_type == TaskType.FEATURE


def test_handle_task_records_history_on_skip(monkeypatch):
    session, _, buffer = _make_session()
    # Simulate user pressing 'n' to skip execution
    monkeypatch.setattr("builtins.input", lambda _: "n")
    session._handle_task("fix the bug")
    assert len(session._history) == 1
    assert session._history[0]["executed"] is False


def test_handle_task_records_history_on_execute(monkeypatch):
    session, _, buffer = _make_session()
    monkeypatch.setattr("builtins.input", lambda _: "y")
    session._handle_task("add tests")
    assert len(session._history) == 1
    assert session._history[0]["executed"] is True
    session.executor.execute.assert_called_once()


def test_handle_task_no_profile_skips_execution():
    buffer = StringIO()
    console = Console(file=buffer, width=120, force_terminal=False, color_system=None)
    service = MagicMock()
    service.classifier = MagicMock()
    service.classifier.classify.return_value = _make_classification()
    service.recommend.return_value = _make_decision()
    service.recommend_from_description.return_value = (_make_decision(), _make_classification())
    executor = MagicMock()
    session = ReplSession(
        config=_make_config(),
        profile_name=None,
        profile=None,
        service=service,
        executor=executor,
        console=console,
    )
    session._handle_task("do something")
    executor.execute.assert_not_called()
    assert "No profile" in buffer.getvalue()


# ---------------------------------------------------------------------------
# Override flow
# ---------------------------------------------------------------------------


def test_ask_override_yes(monkeypatch):
    session, _, _ = _make_session()
    monkeypatch.setattr("builtins.input", lambda _: "y")
    assert session._ask_override() is True


def test_ask_override_no(monkeypatch):
    session, _, _ = _make_session()
    monkeypatch.setattr("builtins.input", lambda _: "n")
    assert session._ask_override() is False


def test_interactive_override_keeps_defaults(monkeypatch):
    session, _, _ = _make_session()
    # Press Enter for every prompt (keep current)
    monkeypatch.setattr("builtins.input", lambda _: "")
    original = _make_classification()
    result = session._interactive_override(original)
    assert result.task_type == original.task_type
    assert result.scope == original.scope
