"""Routing for the supervisor-first main chat graph."""

from __future__ import annotations

from langgraph.prebuilt import tools_condition

from agentbot.graph.state import AgentGraphState


def route_after_supervisor(state: AgentGraphState) -> str:
    """Route the supervisor decision to respond, tools, or browser."""
    decision = state.get("supervisor_decision") or {}
    next_step = str(decision.get("decision") or "respond")
    if next_step == "browser":
        return "browser"
    if next_step == "tools":
        return "tool_chatbot"
    return "respond"


def route_after_tool_chatbot(state: AgentGraphState) -> str:
    """Continue to tools when tool calls exist, otherwise finish the turn."""
    return tools_condition(state)


def get_latest_user_text(state: AgentGraphState) -> str:
    """Return the most recent user message content."""
    messages = state.get("messages", [])
    for message in reversed(messages):
        content = getattr(message, "content", None)
        if content is None:
            continue
        if getattr(message, "type", None) != "human":
            continue
        if isinstance(content, str):
            return content.strip()
        return str(content).strip()
    return ""
