"""Run-oriented streaming runner backed by SQLite transcript and run storage."""

from __future__ import annotations

from typing import Any, Iterator

from agentbot.app.execution_core import (
    execute_graph,
    ExecutionSetupError,
    extract_delta,
    find_final_assistant_message,
    format_graph_error,
    message_metadata,
    new_prefixed_id,
    now_iso,
    prepare_run,
    stringify_message_content,
)
from agentbot.app.graph_runtime_events import apply_runtime_events_from_updates


def stream_once(user_text: str, conversation_id: str) -> Iterator[dict[str, Any]]:
    """Run one turn and emit run-oriented SSE events."""
    try:
        prepared = prepare_run(
            user_text,
            conversation_id=conversation_id,
            streaming=True,
            require_persisted_run=True,
        )
    except ExecutionSetupError as exc:
        yield _ui_event("run_failed", message=str(exc))
        yield _ui_event("done")
        return

    yield _ui_event(
        "run_started",
        run_id=prepared.active_run.run_id,
        conversation_id=conversation_id,
        user_message_id=prepared.user_message_id,
        started_at=prepared.user_timestamp,
        content=user_text,
    )

    final_values: dict[str, Any] | None = None
    emitted_tool_calls: set[str] = set()
    final_message_id: str | None = None

    try:
        for event_type, payload in execute_graph(prepared, stream_mode=["messages", "updates", "values"]):
            if event_type is None:
                continue

            if event_type == "messages":
                delta = extract_delta(payload)
                if delta is None:
                    continue

                if final_message_id is None:
                    final_message_id = new_prefixed_id("msg")
                yield _ui_event(
                    "assistant_final_delta",
                    run_id=prepared.active_run.run_id,
                    message_id=final_message_id,
                    delta=delta,
                )
                continue

            if event_type == "updates":
                prepared.active_run, runtime_events = apply_runtime_events_from_updates(
                    payload,
                    prepared.active_run,
                    prepared.runtime_writer,
                    emitted_tool_calls,
                )
                for event in runtime_events:
                    yield event
                continue

            if event_type == "values" and isinstance(payload, dict):
                final_values = payload
    except Exception as exc:
        prepared.runtime_writer.fail_run(
            prepared.active_run,
            meta=prepared.meta,
            error_message=format_graph_error(exc),
            ended_at=now_iso(),
        )
        yield _ui_event("run_failed", run_id=prepared.active_run.run_id, message=format_graph_error(exc))
        yield _ui_event("done")
        return

    final_messages = final_values.get("messages") if isinstance(final_values, dict) else None
    if not isinstance(final_messages, list):
        prepared.runtime_writer.fail_run(
            prepared.active_run,
            meta=prepared.meta,
            error_message="Streaming run did not produce a final message state.",
            ended_at=now_iso(),
        )
        yield _ui_event(
            "run_failed",
            run_id=prepared.active_run.run_id,
            message="Streaming run did not produce a final message state.",
        )
        yield _ui_event("done")
        return

    final_assistant = find_final_assistant_message(final_messages)
    if final_assistant is None:
        prepared.runtime_writer.fail_run(
            prepared.active_run,
            meta=prepared.meta,
            error_message="No final assistant message was produced.",
            ended_at=now_iso(),
        )
        yield _ui_event(
            "run_failed",
            run_id=prepared.active_run.run_id,
            message="No final assistant message was produced.",
        )
        yield _ui_event("done")
        return

    final_text = stringify_message_content(final_assistant.content)
    assistant_metadata = message_metadata(final_assistant)
    prepared.runtime_writer.complete_run(
        prepared.active_run,
        meta=prepared.meta,
        assistant_message_id=assistant_metadata["message_id"],
        assistant_text=final_text,
        assistant_timestamp=assistant_metadata["timestamp"],
    )

    yield _ui_event(
        "assistant_finalized",
        run_id=prepared.active_run.run_id,
        message_id=assistant_metadata["message_id"],
        timestamp=assistant_metadata["timestamp"],
        content=final_text,
    )
    yield _ui_event(
        "run_completed",
        run_id=prepared.active_run.run_id,
        conversation_id=conversation_id,
        final_message_id=assistant_metadata["message_id"],
        ended_at=assistant_metadata["timestamp"],
    )
    yield _ui_event("done")


def _ui_event(event: str, **payload: Any) -> dict[str, Any]:
    return {"event": event, "data": payload}
