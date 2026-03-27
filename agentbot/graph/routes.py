"""Routing for the current minimal agent loop."""

from __future__ import annotations

from langgraph.prebuilt import tools_condition

from agentbot.graph.state import MessagesState


def route_after_chatbot(state: MessagesState) -> str:
    """Route to the tool node when the model emitted tool calls."""
    return tools_condition(state)
