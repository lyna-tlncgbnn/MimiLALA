"""Search provider adapters."""

from __future__ import annotations

from agentbot.config.settings import SearchSettings
from agentbot.tools.providers.base import SearchProvider
from agentbot.tools.providers.tavily import TavilySearchProvider


def build_search_provider(settings: SearchSettings) -> SearchProvider:
    """Create the configured search provider implementation."""
    provider = settings.provider.strip().lower()
    if provider == "tavily":
        return TavilySearchProvider(
            api_key=settings.api_key,
            max_results=settings.max_results,
            timeout_seconds=settings.timeout_seconds,
        )
    raise ValueError(f"Unsupported search provider: {settings.provider}")
