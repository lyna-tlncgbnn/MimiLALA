"""Tool registry for the current minimal agent."""

from __future__ import annotations

from langchain_core.tools import BaseTool

from agentbot.tools.basic import get_current_time, multiply


def get_registered_tools() -> list[BaseTool]:
    """Return the tool list used by the current graph."""
    return [get_current_time, multiply]
