"""Provider interfaces for search-backed tools."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class SearchResult:
    """Normalized search result used by tool providers."""

    title: str
    url: str
    snippet: str


class SearchProvider(Protocol):
    """Provider contract for web search backends."""

    def search(self, query: str, *, max_results: int | None = None) -> list[SearchResult]:
        """Return normalized search results for the given query."""
