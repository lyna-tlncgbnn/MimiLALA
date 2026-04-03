"""Routing for the current minimal agent loop."""

from __future__ import annotations

from langgraph.prebuilt import tools_condition

from agentbot.graph.state import MessagesState


def route_after_intent(state: MessagesState) -> str:
    """Route into the browser subgraph when an explicit browser task was detected."""
    if state.get("browser_task"):
        return "browser_subgraph"
    return "chatbot"


def route_after_chatbot(state: MessagesState) -> str:
    """Route to the tool node when the model emitted tool calls."""
    return tools_condition(state)
