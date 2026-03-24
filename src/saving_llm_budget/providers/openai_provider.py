"""OpenAI provider — real streaming chat implementation."""

from __future__ import annotations

import os
from typing import Iterator

from .. import constants
from ..models import Provider, TaskRequest
from .base import ProviderAdapter, ProviderExecutionResult, ProviderPlan


class OpenAIAdapter(ProviderAdapter):
    """Legacy adapter stub — kept for executor compatibility."""

    provider = Provider.CODEX

    def plan(self, task: TaskRequest) -> ProviderPlan:
        raise NotImplementedError

    def execute(self, task: TaskRequest, plan: ProviderPlan | None = None) -> ProviderExecutionResult:
        raise NotImplementedError


class OpenAIChatAdapter:
    """Streaming chat adapter for OpenAI models."""

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.getenv(constants.OPENAI_API_KEY_VAR) or ""
        self._last_input_tokens = 0
        self._last_output_tokens = 0

    def stream(
        self,
        model_id: str,
        messages: list[dict],
        system: str | None = None,
    ) -> Iterator[str]:
        """Yield text chunks from a streaming OpenAI response."""
        from openai import OpenAI

        client = OpenAI(api_key=self._api_key)

        full_messages = list(messages)
        if system:
            full_messages = [{"role": "system", "content": system}] + full_messages

        accumulated_text = ""
        response = client.chat.completions.create(
            model=model_id,
            messages=full_messages,  # type: ignore[arg-type]
            stream=True,
            stream_options={"include_usage": True},
        )
        for chunk in response:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                accumulated_text += delta.content
                yield delta.content
            if chunk.usage:
                self._last_input_tokens = chunk.usage.prompt_tokens
                self._last_output_tokens = chunk.usage.completion_tokens

    @property
    def last_usage(self) -> tuple[int, int]:
        return self._last_input_tokens, self._last_output_tokens
