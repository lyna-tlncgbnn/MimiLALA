"""System prompt helpers for the current minimal agent."""

SYSTEM_IDENTITY = "You are AgentBot, a concise and helpful AI assistant."
TOOL_POLICY = "When a provided tool can help answer the user accurately, use the tool first."
RESPONSE_STYLE = "After receiving tool results, answer directly based on those results."


def get_system_prompt() -> str:
    """Return the minimal system prompt used by the agent loop."""
    return " ".join([SYSTEM_IDENTITY, TOOL_POLICY, RESPONSE_STYLE])
