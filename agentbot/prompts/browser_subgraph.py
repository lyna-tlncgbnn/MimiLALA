"""Compatibility helpers for browser prompt loading."""

from __future__ import annotations

from agentbot.prompts.browser.loader import load_browser_prompt


def get_browser_subgraph_system_prompt(max_steps: int) -> str:
    """Load the browser planner prompt from the prompt template directory."""
    return load_browser_prompt("system_prompt_no_thinking.md", max_steps=max_steps)


def get_browser_router_prompt() -> str:
    """Load the router prompt used for model-guided entry routing."""
    return load_browser_prompt("router_prompt.md")
