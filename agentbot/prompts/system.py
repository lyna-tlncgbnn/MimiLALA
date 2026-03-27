"""System prompt helpers for the current minimal agent."""


def get_system_prompt() -> str:
    """Return the minimal system prompt used by the agent loop."""
    return (
        "You are AgentBot, a concise and helpful AI assistant. "
        "When a provided tool can help answer the user accurately, use the tool first. "
        "After receiving tool results, answer based on those results."
    )
