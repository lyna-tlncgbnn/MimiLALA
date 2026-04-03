"""Graph state definitions."""

from __future__ import annotations

import operator
from typing import Any

from langgraph.graph import MessagesState as LangGraphMessagesState
from typing_extensions import Annotated


class AgentGraphState(LangGraphMessagesState):
    """Top-level graph state with browser-subgraph fields."""

    browser_task: str | None
    browser_intent_reason: str | None
    browser_status: str | None
    browser_result: str | None
    browser_summary: str | None
    browser_session_id: str | None
    browser_current_url: str | None
    browser_parent_step_key: str | None
    browser_state_summary: dict[str, Any] | None
    browser_pending_action: dict[str, Any] | None
    browser_pending_actions: list[dict[str, Any]] | None
    browser_last_action_result: dict[str, Any] | None
    browser_last_action_results: list[dict[str, Any]] | None
    browser_action_history: list[dict[str, Any]] | None
    browser_action_count: int | None
    browser_max_actions: int | None
    browser_max_actions_per_step: int | None
    browser_page_fingerprint: str | None
    browser_stagnant_count: int | None
    browser_loop_signal: str | None
    browser_requires_approval: bool | None
    browser_approval_reason: str | None
    browser_failure_reason: str | None
    browser_failure_step: str | None
    browser_evaluation_previous_goal: str | None
    browser_memory: str | None
    browser_next_goal: str | None
    browser_progress_signal: str | None
    browser_consecutive_failures: int | None
    browser_plan: list[dict[str, Any]] | None
    browser_current_plan_item: int | None
    browser_plan_generation_step: int | None
    browser_events: Annotated[list[dict[str, Any]], operator.add]


MessagesState = AgentGraphState

__all__ = ["AgentGraphState", "MessagesState"]
