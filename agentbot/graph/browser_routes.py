"""Routing helpers for the browser subgraph."""

from __future__ import annotations

from agentbot.graph.state import AgentGraphState


def route_after_browser_decide(state: AgentGraphState) -> str:
    if state.get("browser_requires_approval"):
        return "browser_finish"
    action = state.get("browser_pending_action") or {}
    action_type = str(action.get("action_type") or "done")
    if action_type == "done":
        return "browser_finish"
    return "browser_act"


def route_after_browser_evaluate(state: AgentGraphState) -> str:
    action = state.get("browser_pending_action") or {}
    action_type = str(action.get("action_type") or "done")
    if action_type == "done":
        return "browser_finish"
    action_count = int(state.get("browser_action_count") or 0)
    max_actions = int(state.get("browser_max_actions") or 4)
    if action_count >= max_actions:
        return "browser_finish"
    return "browser_observe"
