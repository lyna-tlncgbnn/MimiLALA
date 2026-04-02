"""Run-oriented streaming runner backed by SQLite transcript and run storage."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterator
from uuid import uuid4

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage

from agentbot.config.settings import Settings
from agentbot.graph.builder import build_graph
from agentbot.graph.checkpoints import sqlite_checkpointer, thread_config, thread_has_checkpoints
from agentbot.models.llm import build_llm
from agentbot.prompts.system import get_system_prompt
from agentbot.services.sqlite_conversations import SQLiteConversationService
from agentbot.storage.common import AGENTBOT_META_KEY
from agentbot.storage.shadow_runtime import ActiveRunShadow, RuntimeShadowWriter
from agentbot.tools.infra.error_handling import is_tool_error_output


def stream_once(user_text: str, conversation_id: str) -> Iterator[dict[str, Any]]:
    """Run one turn and emit run-oriented SSE events."""
    try:
        settings = Settings.from_file()
    except ValueError as exc:
        yield _ui_event("run_failed", message=str(exc))
        yield _ui_event("done")
        return

    try:
        llm = build_llm(settings, streaming=True)
    except Exception as exc:
        yield _ui_event("run_failed", message=f"Failed to initialize chat model: {exc}")
        yield _ui_event("done")
        return

    conversation_service = SQLiteConversationService()
    runtime_writer = RuntimeShadowWriter()

    try:
        meta, _messages = conversation_service.get_conversation(conversation_id)
    except Exception as exc:
        yield _ui_event("run_failed", message=f"Failed to load conversation history: {exc}")
        yield _ui_event("done")
        return

    thread_id = meta.conversation_id
    user_message_id = _new_prefixed_id("msg")
    user_timestamp = _now_iso()
    user_message = HumanMessage(
        content=user_text,
        additional_kwargs={
            AGENTBOT_META_KEY: {
                "message_id": user_message_id,
                "timestamp": user_timestamp,
            }
        },
    )
    active_run = _safe_start_run(runtime_writer, meta=meta, user_message=user_message)
    if active_run is None:
        yield _ui_event("run_failed", message="Failed to start run persistence.")
        yield _ui_event("done")
        return

    yield _ui_event(
        "run_started",
        run_id=active_run.run_id,
        conversation_id=conversation_id,
        user_message_id=user_message_id,
        started_at=user_timestamp,
        content=user_text,
    )

    final_values: dict[str, Any] | None = None
    emitted_tool_calls: set[str] = set()
    final_message_id: str | None = None
    final_message_started = False
    final_text_fragments: list[str] = []

    try:
        with sqlite_checkpointer() as checkpointer:
            seeded_from_transcript = not thread_has_checkpoints(checkpointer, thread_id)
            input_messages = _build_input_messages(
                conversation_service=conversation_service,
                conversation_id=meta.conversation_id,
                user_message=user_message,
                seed_from_transcript=seeded_from_transcript,
            )
            graph = build_graph(llm, checkpointer=checkpointer)

            for chunk in graph.stream(
                {"messages": input_messages},
                config=thread_config(thread_id),
                stream_mode=["messages", "updates", "values"],
                version="v2",
            ):
                event_type, payload = _normalize_stream_chunk(chunk)
                if event_type is None:
                    continue

                if event_type == "messages":
                    delta = _extract_delta(payload)
                    if delta is None:
                        continue

                    if not final_message_started:
                        final_message_started = True
                        final_message_id = _new_prefixed_id("msg")
                    final_text_fragments.append(delta)
                    yield _ui_event(
                        "assistant_final_delta",
                        run_id=active_run.run_id,
                        message_id=final_message_id,
                        delta=delta,
                    )
                    continue

                if event_type == "updates":
                    for event in _step_events_from_updates(payload, active_run, runtime_writer, emitted_tool_calls):
                        yield event
                    continue

                if event_type == "values" and isinstance(payload, dict):
                    final_values = payload
    except Exception as exc:
        runtime_writer.fail_run(
            active_run,
            meta=meta,
            error_message=_format_graph_error(exc),
            ended_at=_now_iso(),
        )
        yield _ui_event("run_failed", run_id=active_run.run_id, message=_format_graph_error(exc))
        yield _ui_event("done")
        return

    final_messages = final_values.get("messages") if isinstance(final_values, dict) else None
    if not isinstance(final_messages, list):
        runtime_writer.fail_run(
            active_run,
            meta=meta,
            error_message="Streaming run did not produce a final message state.",
            ended_at=_now_iso(),
        )
        yield _ui_event(
            "run_failed",
            run_id=active_run.run_id,
            message="Streaming run did not produce a final message state.",
        )
        yield _ui_event("done")
        return

    final_assistant = _find_final_assistant_message(final_messages)
    if final_assistant is None:
        runtime_writer.fail_run(
            active_run,
            meta=meta,
            error_message="No final assistant message was produced.",
            ended_at=_now_iso(),
        )
        yield _ui_event("run_failed", run_id=active_run.run_id, message="No final assistant message was produced.")
        yield _ui_event("done")
        return

    final_text = _stringify_message_content(final_assistant.content)
    assistant_metadata = _message_metadata(final_assistant)
    final_message_id = assistant_metadata["message_id"]
    runtime_writer.complete_run(
        active_run,
        meta=meta,
        assistant_message_id=assistant_metadata["message_id"],
        assistant_text=final_text,
        assistant_timestamp=assistant_metadata["timestamp"],
    )

    yield _ui_event(
        "assistant_finalized",
        run_id=active_run.run_id,
        message_id=assistant_metadata["message_id"],
        timestamp=assistant_metadata["timestamp"],
        content=final_text,
    )
    yield _ui_event(
        "run_completed",
        run_id=active_run.run_id,
        conversation_id=conversation_id,
        final_message_id=assistant_metadata["message_id"],
        ended_at=assistant_metadata["timestamp"],
    )
    yield _ui_event("done")


def _step_events_from_updates(
    payload: Any,
    active_run: ActiveRunShadow,
    runtime_writer: RuntimeShadowWriter,
    emitted_tool_calls: set[str],
) -> Iterator[dict[str, Any]]:
    if not isinstance(payload, dict):
        return

    for node_update in payload.values():
        if not isinstance(node_update, dict):
            continue

        messages = node_update.get("messages")
        if messages is None:
            continue
        if not isinstance(messages, list):
            messages = [messages]

        for message in messages:
            if isinstance(message, AIMessage) and message.tool_calls:
                metadata = _message_metadata(message)
                for tool_call in message.tool_calls:
                    tool_call_id = str(tool_call.get("id") or _new_prefixed_id("call"))
                    if tool_call_id in emitted_tool_calls:
                        continue
                    emitted_tool_calls.add(tool_call_id)
                    active_run = runtime_writer.record_tool_started(
                        active_run,
                        tool_call_id=tool_call_id,
                        tool_name=str(tool_call.get("name") or "unknown_tool"),
                        args=tool_call.get("args") or {},
                        timestamp=metadata["timestamp"],
                    )
                    step_id = active_run.tool_steps.get(tool_call_id)
                    yield _ui_event(
                        "step_started",
                        run_id=active_run.run_id,
                        step_id=step_id,
                        step_type="tool_call",
                        title=f"Running {str(tool_call.get('name') or 'unknown_tool')}",
                        status="running",
                        display_mode="timeline",
                        tool_name=str(tool_call.get("name") or "unknown_tool"),
                        tool_call_id=tool_call_id,
                        args=tool_call.get("args") or {},
                        timestamp=metadata["timestamp"],
                    )
            elif isinstance(message, ToolMessage):
                metadata = _message_metadata(message)
                tool_output = _stringify_message_content(message.content)
                failed = is_tool_error_output(tool_output)
                active_run = runtime_writer.record_tool_finished(
                    active_run,
                    tool_call_id=str(message.tool_call_id or ""),
                    tool_name=message.name or "unknown_tool",
                    tool_output=tool_output,
                    timestamp=metadata["timestamp"],
                    failed=failed,
                )
                step_id = active_run.tool_steps.get(str(message.tool_call_id or ""))
                yield _ui_event(
                    "step_completed",
                    run_id=active_run.run_id,
                    step_id=step_id,
                    step_type="tool_call",
                    title=f"Running {message.name or 'unknown_tool'}",
                    status="failed" if failed else "completed",
                    tool_name=message.name or "unknown_tool",
                    tool_call_id=str(message.tool_call_id or ""),
                    output=tool_output,
                    timestamp=metadata["timestamp"],
                )


def _build_input_messages(
    *,
    conversation_service: SQLiteConversationService,
    conversation_id: str,
    user_message: HumanMessage,
    seed_from_transcript: bool,
) -> list[BaseMessage]:
    if not seed_from_transcript:
        return [user_message]
    history = conversation_service.get_conversation_history_messages(conversation_id)
    return [
        SystemMessage(content=get_system_prompt()),
        *history,
        user_message,
    ]


def _find_final_assistant_message(messages: list[BaseMessage]) -> AIMessage | None:
    for message in reversed(messages):
        if isinstance(message, AIMessage) and _stringify_message_content(message.content):
            return message
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            return message
    return None


def _extract_delta(payload: Any) -> str | None:
    if not isinstance(payload, tuple) or len(payload) != 2:
        return None
    token, metadata = payload
    if not isinstance(metadata, dict):
        return None
    if metadata.get("langgraph_node") != "chatbot":
        return None
    text = _stringify_message_content(getattr(token, "content", token))
    return text if text else None


def _stringify_message_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_chunks: list[str] = []
        for item in content:
            if isinstance(item, str):
                text_chunks.append(item)
            elif isinstance(item, dict) and item.get("type") == "text":
                text_chunks.append(str(item.get("text", "")))
        return "".join(text_chunks)
    return str(content) if content is not None else ""


def _format_graph_error(exc: Exception) -> str:
    message = str(exc)
    if message.startswith("Model execution failed:"):
        return message
    if message.startswith("Tool execution failed:"):
        return message
    return f"Graph execution failed: {message}"


def _ui_event(event: str, **payload: Any) -> dict[str, Any]:
    return {"event": event, "data": payload}


def _normalize_stream_chunk(chunk: Any) -> tuple[str | None, Any]:
    if isinstance(chunk, tuple) and len(chunk) == 2 and isinstance(chunk[0], str):
        return chunk[0], chunk[1]
    if isinstance(chunk, dict):
        event_type = chunk.get("type")
        if isinstance(event_type, str):
            return event_type, chunk.get("data")
    return None, None


def _message_metadata(message: BaseMessage) -> dict[str, str]:
    metadata = dict(getattr(message, "additional_kwargs", {}).get(AGENTBOT_META_KEY) or {})
    return {
        "message_id": str(metadata.get("message_id") or _new_prefixed_id("msg")),
        "timestamp": str(metadata.get("timestamp") or _now_iso()),
    }


def _safe_start_run(
    runtime_writer: RuntimeShadowWriter,
    *,
    meta,
    user_message: HumanMessage,
) -> ActiveRunShadow | None:
    try:
        metadata = _message_metadata(user_message)
        return runtime_writer.start_run(
            meta=meta,
            user_message_id=metadata["message_id"],
            user_text=_stringify_message_content(user_message.content),
            user_timestamp=metadata["timestamp"],
        )
    except Exception:
        return None


def _new_prefixed_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")
