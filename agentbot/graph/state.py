"""Graph state definitions."""

from __future__ import annotations

from langgraph.graph import MessagesState


class AgentGraphState(MessagesState, total=False):
    """Main chat graph state with orchestration metadata."""

    supervisor_decision: dict | None
    browser_task_request: dict | None
    browser_task_result: dict | None


__all__ = ["AgentGraphState", "MessagesState"]
