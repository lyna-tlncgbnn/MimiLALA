"""Explicit browser task service powered by the browser subgraph."""

from __future__ import annotations

from agentbot.config.settings import Settings
from agentbot.graph.browser_builder import build_browser_graph
from agentbot.models.browser import BrowserTaskResult
from agentbot.models.llm import build_llm


class BrowserTaskService:
    """Run explicit browser automation tasks without changing the main chat graph."""

    def run_task(self, task: str, start_url: str | None = None, max_steps: int = 5) -> BrowserTaskResult:
        try:
            settings = Settings.from_file()
            llm = build_llm(settings)
            graph = build_browser_graph(llm)
            result = graph.invoke(
                {
                    "task": task,
                    "start_url": start_url,
                    "llm_config": {
                        "api_key": settings.openai_api_key,
                        "base_url": settings.openai_base_url,
                        "model": settings.model,
                    },
                    "max_steps": max_steps,
                }
            )
            return BrowserTaskResult(
                status=result.get("status", "failed"),
                final_response=result.get("final_response"),
                error_message=result.get("error_message"),
                current_url=result.get("current_url"),
                page_title=result.get("page_title"),
                step_count=int(result.get("step_count", 0)),
                steps=result.get("steps", []),
            )
        except Exception as exc:
            return BrowserTaskResult(
                status="failed",
                final_response=None,
                error_message=str(exc),
                current_url=None,
                page_title=None,
                step_count=0,
                steps=[],
            )
