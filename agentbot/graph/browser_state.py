"""Typed state for the browser subgraph."""

from __future__ import annotations

from typing import TypedDict


class BrowserSubgraphState(TypedDict, total=False):
    task: str
    start_url: str | None
    llm_config: dict | None
    browser_session_id: str | None
    current_url: str | None
    page_title: str | None
    browser_state_summary: dict | None
    selector_map_digest: str | None
    last_action: dict | None
    last_action_result: dict | None
    step_count: int
    max_steps: int
    status: str
    final_response: str | None
    error_message: str | None
    steps: list[dict]
