"""Claude provider — real streaming chat implementation."""

from __future__ import annotations

import os
from typing import Iterator

from .. import constants
from ..models import Provider, TaskRequest
from .base import ProviderAdapter, ProviderExecutionResult, ProviderPlan


class ClaudeAdapter(ProviderAdapter):
    provider = Provider.CLAUDE

    def plan(self, task: TaskRequest) -> ProviderPlan:
        raise NotImplementedError

    def execute(self, task: TaskRequest, plan: ProviderPlan | None = None) -> ProviderExecutionResult:
        raise NotImplementedError


class ClaudeChatAdapter:
    """Streaming chat adapter for Claude models."""

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.getenv(constants.ANTHROPIC_API_KEY_VAR) or ""

    def stream(
        self,
        model_id: str,
        messages: list[dict],
        system: str | None = None,
    ) -> Iterator[str]:
        """Yield text chunks from a streaming Claude response."""
        import anthropic

        client = anthropic.Anthropic(api_key=self._api_key)
        kwargs: dict = dict(
            model=model_id,
            max_tokens=constants.CHAT_MAX_TOKENS,
            messages=messages,
        )
        if system:
            kwargs["system"] = system

        with client.messages.stream(**kwargs) as stream:
            for text in stream.text_stream:
                yield text
            # Capture final usage
            final = stream.get_final_message()
            self._last_input_tokens = final.usage.input_tokens
            self._last_output_tokens = final.usage.output_tokens

    @property
    def last_usage(self) -> tuple[int, int]:
        """Return (input_tokens, output_tokens) from the most recent call."""
        return getattr(self, "_last_input_tokens", 0), getattr(self, "_last_output_tokens", 0)
