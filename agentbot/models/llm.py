"""Chat model factory."""

from __future__ import annotations

from langchain_openai import ChatOpenAI

from agentbot.config.settings import Settings


def build_llm(settings: Settings) -> ChatOpenAI:
    """Create the chat model from the current project settings."""
    return ChatOpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        model=settings.model,
        temperature=settings.temperature,
    )
