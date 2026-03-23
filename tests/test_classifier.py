"""Tests for the LLM task classifier."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from saving_llm_budget.models import Clarity, Priority, Scope, TaskType
from saving_llm_budget.services.classifier import TaskClassifier, _parse_response, _safe_enum


# ---------------------------------------------------------------------------
# Unit: helpers
# ---------------------------------------------------------------------------


def test_safe_enum_valid():
    assert _safe_enum(TaskType, "bugfix", TaskType.FEATURE) == TaskType.BUGFIX


def test_safe_enum_invalid_falls_back():
    assert _safe_enum(TaskType, "garbage", TaskType.FEATURE) == TaskType.FEATURE


def test_parse_response_plain_json():
    raw = '{"task_type":"bugfix","scope":"single_file"}'
    data = _parse_response(raw)
    assert data["task_type"] == "bugfix"


def test_parse_response_strips_markdown_fences():
    raw = "```json\n{\"task_type\":\"test\"}\n```"
    data = _parse_response(raw)
    assert data["task_type"] == "test"


# ---------------------------------------------------------------------------
# Unit: fallback classification (no API key)
# ---------------------------------------------------------------------------


@pytest.fixture()
def classifier():
    return TaskClassifier()


def test_fallback_bugfix(classifier, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = classifier.classify("Fix the null pointer crash in main.py")
    assert result.task_type == TaskType.BUGFIX
    assert result.used_llm is False


def test_fallback_refactor(classifier, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = classifier.classify("Refactor the payment module")
    assert result.task_type == TaskType.REFACTOR


def test_fallback_explain(classifier, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = classifier.classify("Explain how the auth middleware works")
    assert result.task_type == TaskType.EXPLAIN


def test_fallback_repo_wide_scope(classifier, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = classifier.classify("Update all tests across the entire repo")
    assert result.scope == Scope.REPO_WIDE


def test_fallback_single_file_scope(classifier, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = classifier.classify("Fix line 42 in the file")
    assert result.scope == Scope.SINGLE_FILE


def test_fallback_reasoning_mentions_key(classifier, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = classifier.classify("do something")
    assert "ANTHROPIC_API_KEY" in result.reasoning


# ---------------------------------------------------------------------------
# Unit: LLM path (mocked API)
# ---------------------------------------------------------------------------


def _mock_response(payload: dict):
    content_block = MagicMock()
    content_block.text = json.dumps(payload)
    message = MagicMock()
    message.content = [content_block]
    return message


def test_llm_path_happy(classifier, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    payload = {
        "task_type": "feature",
        "scope": "module",
        "clarity": "very_clear",
        "priority": "balanced",
        "long_context": True,
        "auto_modify": False,
        "reasoning": "New feature spanning a module.",
    }
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _mock_response(payload)

    with patch("anthropic.Anthropic", return_value=mock_client):
        result = classifier.classify("Add OAuth2 support to the auth module")

    assert result.task_type == TaskType.FEATURE
    assert result.scope == Scope.MODULE
    assert result.clarity == Clarity.VERY_CLEAR
    assert result.long_context is True
    assert result.auto_modify is False
    assert result.used_llm is True


def test_llm_path_invalid_enum_falls_back_to_default(classifier, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    payload = {
        "task_type": "NONEXISTENT",
        "scope": "few_files",
        "clarity": "very_clear",
        "priority": "balanced",
        "long_context": False,
        "auto_modify": False,
        "reasoning": "test",
    }
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _mock_response(payload)

    with patch("anthropic.Anthropic", return_value=mock_client):
        result = classifier.classify("do something")

    assert result.task_type == TaskType.FEATURE  # safe fallback


def test_llm_path_api_error_falls_back(classifier, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")

    mock_client = MagicMock()
    mock_client.messages.create.side_effect = RuntimeError("network error")

    with patch("anthropic.Anthropic", return_value=mock_client):
        result = classifier.classify("do something")

    assert result.used_llm is False
