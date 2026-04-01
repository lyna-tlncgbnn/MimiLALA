"""Conditional routes for the browser subgraph."""

from __future__ import annotations

from agentbot.graph.browser_state import BrowserSubgraphState
from agentbot.models.browser import BrowserActionPlan


def route_after_browser_plan(state: BrowserSubgraphState) -> str:
    """Finish when the planner emits done, otherwise execute the action."""
    action = BrowserActionPlan.model_validate(state.get("last_action") or {})
    if action.action_type == "done":
        return "finish"
    return "act"


def route_after_browser_act(state: BrowserSubgraphState) -> str:
    """Loop until max_steps is hit or an error occurs."""
    if state.get("status") == "failed":
        return "finish"
    if int(state.get("step_count", 0)) >= int(state.get("max_steps", 5)):
        return "finish"
    return "observe"
