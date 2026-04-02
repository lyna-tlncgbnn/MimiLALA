"""Shared tool error handling helpers for LangGraph ToolNode."""

from __future__ import annotations

TOOL_ERROR_PREFIX = "Tool execution error:"
TOOL_ERROR_RECOVERY_HINT = (
    "The tool did not complete successfully. Explain the issue, adjust the arguments, "
    "or use a different tool if appropriate."
)


def format_tool_error(exc: Exception) -> str:
    """Convert most tool exceptions into a ToolMessage-friendly error string."""
    if isinstance(exc, MemoryError):
        raise exc

    detail = str(exc).strip() or exc.__class__.__name__
    return (
        f"{TOOL_ERROR_PREFIX} {detail}\n\n"
        f"{TOOL_ERROR_RECOVERY_HINT}"
    )


def is_tool_error_output(content: str) -> bool:
    """Check whether a tool output string represents a handled tool failure."""
    return content.startswith(TOOL_ERROR_PREFIX)
