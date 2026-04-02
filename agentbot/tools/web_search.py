"""Web search tools backed by pluggable providers."""

from __future__ import annotations

from langchain_core.tools import tool

from agentbot.config.settings import Settings
from agentbot.tools.providers import build_search_provider

MAX_QUERY_LENGTH = 300


def _load_search_provider():
    settings = Settings.from_file()
    if settings.search is None:
        raise ValueError(
            "Search is not configured. Add a 'search' section to config.json before using web_search."
        )
    return build_search_provider(settings.search), settings.search


def _format_results(query: str, provider_name: str, results) -> str:
    lines = [
        f"Query: {query}",
        f"Provider: {provider_name}",
    ]
    if not results:
        lines.append("Results: none")
        return "\n".join(lines)

    lines.append(f"Results ({len(results)}):")
    for index, result in enumerate(results, start=1):
        lines.append(f"{index}. Title: {result.title}")
        if result.url:
            lines.append(f"   URL: {result.url}")
        if result.snippet:
            lines.append(f"   Snippet: {result.snippet}")
    return "\n".join(lines)


@tool
def web_search(query: str, max_results: int = 5) -> str:
    """Search the public web and return a concise list of relevant results."""
    normalized_query = query.strip()
    if not normalized_query:
        raise ValueError("query must not be empty.")
    if len(normalized_query) > MAX_QUERY_LENGTH:
        raise ValueError(f"query must be at most {MAX_QUERY_LENGTH} characters.")
    if max_results < 1 or max_results > 10:
        raise ValueError("max_results must be between 1 and 10.")

    provider, search_settings = _load_search_provider()
    results = provider.search(normalized_query, max_results=max_results)
    return _format_results(normalized_query, search_settings.provider, results)


TOOLS = [web_search]
