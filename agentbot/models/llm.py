"""Chat model factory."""

from __future__ import annotations

from langchain_openai import ChatOpenAI

from agentbot.config.settings import Settings


def build_llm(settings: Settings, streaming: bool = False) -> ChatOpenAI:
    """Create the chat model from the current project settings."""
    kwargs: dict[str, object] = {
        "api_key": settings.openai_api_key,
        "base_url": settings.openai_base_url,
        "model": settings.model,
        "temperature": settings.temperature,
        "top_p": settings.top_p,
        "frequency_penalty": settings.frequency_penalty,
        "presence_penalty": settings.presence_penalty,
        "max_retries": settings.max_retries,
        "streaming": streaming,
    }
    if settings.max_tokens is not None:
        kwargs["max_tokens"] = settings.max_tokens
    if settings.request_timeout_seconds is not None:
        kwargs["request_timeout"] = settings.request_timeout_seconds
    if settings.reasoning_effort:
        kwargs["reasoning_effort"] = settings.reasoning_effort
    if settings.reasoning:
        kwargs["reasoning"] = settings.reasoning
    if settings.extra_body:
        kwargs["extra_body"] = settings.extra_body
    if settings.default_headers:
        kwargs["default_headers"] = settings.default_headers

    return ChatOpenAI(
        **kwargs,
    )
