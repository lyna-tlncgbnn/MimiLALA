"""Runner for single-turn execution backed by SQLite transcript and run storage."""

from __future__ import annotations

from agentbot.app.debug import DebugPrinter
from agentbot.app.execution_core import (
    best_effort,
    execute_graph,
    ExecutionSetupError,
    extract_final_text,
    format_graph_error,
    now_iso,
    persist_run_outcome,
    prepare_run,
)
from agentbot.app.graph_runtime_events import apply_runtime_events_from_updates
from agentbot.tools.registry import get_registered_tools


class AgentBotError(RuntimeError):
    """User-facing runtime error."""


def run_once(user_text: str, conversation_id: str | None = None) -> str:
    """Run a single LangGraph turn and return the assistant response."""
    try:
        prepared = prepare_run(
            user_text,
            conversation_id=conversation_id,
            streaming=False,
            require_persisted_run=False,
        )
    except ExecutionSetupError as exc:
        raise AgentBotError(str(exc)) from exc

    debug = DebugPrinter(enabled=prepared.settings.debug)
    tools = get_registered_tools()

    debug.log(f"tools registered: {', '.join(tool.name for tool in tools)}")
    debug.log("graph execution started")
    debug.log("loaded conversation state: transcript seed (per-run thread)")

    emitted_tool_calls: set[str] = set()
    final_values: dict | None = None

    try:
        for event_type, payload in execute_graph(prepared, stream_mode=["updates", "values"]):
            if event_type == "updates" and prepared.active_run is not None:
                prepared.active_run, _runtime_events = apply_runtime_events_from_updates(
                    payload,
                    prepared.active_run,
                    prepared.runtime_writer,
                    emitted_tool_calls,
                )
            elif event_type == "values" and isinstance(payload, dict):
                final_values = payload
    except Exception as exc:
        if prepared.active_run is not None:
            best_effort(
                lambda: prepared.runtime_writer.fail_run(
                    prepared.active_run,
                    meta=prepared.meta,
                    error_message=format_graph_error(exc),
                    ended_at=now_iso(),
                )
            )
        raise AgentBotError(format_graph_error(exc)) from exc

    result = final_values or {}
    final_messages = result["messages"]

    if prepared.active_run is not None:
        best_effort(
            lambda: persist_run_outcome(
                runtime_writer=prepared.runtime_writer,
                active_run=prepared.active_run,
                meta=prepared.meta,
                final_messages=final_messages,
            )
        )

    try:
        return extract_final_text(final_messages)
    except RuntimeError as exc:
        raise AgentBotError(str(exc)) from exc
