"""Tavily-backed search provider."""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from agentbot.tools.providers.base import SearchProvider, SearchResult

TAVILY_SEARCH_URL = "https://api.tavily.com/search"


class TavilySearchProvider(SearchProvider):
    """Minimal Tavily adapter for agent-friendly web search."""

    def __init__(self, *, api_key: str, max_results: int = 5, timeout_seconds: float = 12.0):
        self.api_key = api_key.strip()
        self.max_results = max_results
        self.timeout_seconds = timeout_seconds

    def search(self, query: str, *, max_results: int | None = None) -> list[SearchResult]:
        if not self.api_key:
            raise ValueError("Search provider 'tavily' requires search.api_key in config.json.")

        payload = {
            "api_key": self.api_key,
            "query": query,
            "search_depth": "basic",
            "max_results": max_results or self.max_results,
            "include_answer": False,
            "include_raw_content": False,
        }
        body = json.dumps(payload).encode("utf-8")
        request = Request(
            TAVILY_SEARCH_URL,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                response_body = response.read().decode("utf-8")
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore").strip()
            raise RuntimeError(
                f"Tavily search request failed with HTTP {exc.code}"
                + (f": {detail}" if detail else "")
            ) from exc
        except URLError as exc:
            raise RuntimeError(f"Tavily search request failed: {exc.reason}") from exc

        try:
            payload = json.loads(response_body)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Tavily search returned invalid JSON.") from exc

        raw_results = payload.get("results")
        if not isinstance(raw_results, list):
            raise RuntimeError("Tavily search response did not include a results list.")

        results: list[SearchResult] = []
        for item in raw_results:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            url = str(item.get("url") or "").strip()
            snippet = str(item.get("content") or item.get("snippet") or "").strip()
            if not title and not url:
                continue
            results.append(
                SearchResult(
                    title=title or url,
                    url=url,
                    snippet=snippet,
                )
            )
        return results
