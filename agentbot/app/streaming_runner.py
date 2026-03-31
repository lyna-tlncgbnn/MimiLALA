"""Streaming runner for single-turn chat with SSE-friendly events."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterator
from uuid import uuid4

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage

from agentbot.app.debug import DebugPrinter
from agentbot.config.settings import Settings
from agentbot.graph.builder import build_graph
from agentbot.memory.conversation import AGENTBOT_META_KEY, ConversationStore
from agentbot.memory.execution import ExecutionStore, build_event, new_execution_id
from agentbot.models.llm import build_llm
from agentbot.prompts.system import get_system_prompt
from agentbot.tools.registry import get_registered_tools


def stream_once(user_text: str, conversation_id: str) -> Iterator[dict[str, Any]]:
    """Run one LangGraph turn and yield frontend-facing streaming events."""
    try:
        settings = Settings.from_file()
    except ValueError as exc:
        yield _ui_event("error", message=str(exc))
        yield _ui_event("done")
        return

    debug = DebugPrinter(enabled=settings.debug)

    try:
        llm = build_llm(settings, streaming=True)
    except Exception as exc:
        yield _ui_event("error", message=f"Failed to initialize chat model: {exc}")
        yield _ui_event("done")
        return

    conversation_store = ConversationStore()
    execution_store = ExecutionStore()
    tools = get_registered_tools()
    events: list[dict[str, Any]] = []

    try:
        meta, history = conversation_store.get_conversation(conversation_id)
    except Exception as exc:
        yield _ui_event("error", message=f"Failed to load conversation history: {exc}")
        yield _ui_event("done")
        return

    execution_id = new_execution_id()
    events.append(build_event(execution_id, "conversation_loaded", message_count=len(history)))
    events.append(
        build_event(
            execution_id,
            "tools_registered",
            tools=[tool.name for tool in tools],
        )
    )
    events.append(build_event(execution_id, "graph_started"))
    for event in events:
        debug.log_event(event)

    try:
        graph = build_graph(llm)
    except Exception as exc:
        yield _ui_event("error", message=f"Failed to build graph: {exc}")
        yield _ui_event("done")
        return

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

    yield _ui_event(
        "user_message_accepted",
        conversation_id=conversation_id,
        message_id=user_message_id,
        timestamp=user_timestamp,
        content=user_text,
    )

    waiting_timestamp = _now_iso()
    yield _ui_event(
        "assistant_waiting",
        conversation_id=conversation_id,
        timestamp=waiting_timestamp,
    )

    input_messages: list[BaseMessage] = [
        SystemMessage(content=get_system_prompt()),
        *history,
        user_message,
    ]

    final_values: dict[str, Any] | None = None
    assistant_message_id: str | None = None
    assistant_timestamp: str | None = None
    assistant_started = False
    assistant_fragments: list[str] = []
    completed_tool_messages: list[ToolMessage] = []
    emitted_tool_calls: set[str] = set()

    try:
        for chunk in graph.stream(
            {"messages": input_messages},
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

                if not assistant_started:
                    assistant_started = True
                    assistant_message_id = _new_prefixed_id("msg")
                    assistant_timestamp = _now_iso()
                    yield _ui_event(
                        "assistant_message_started",
                        message_id=assistant_message_id,
                        timestamp=assistant_timestamp,
                    )

                assistant_fragments.append(delta)
                yield _ui_event(
                    "assistant_delta",
                    message_id=assistant_message_id,
                    delta=delta,
                )
                continue

            if event_type == "updates":
                for event in _events_from_updates(payload, emitted_tool_calls):
                    if event["event"] == "tool_started":
                        # A new tool phase means any later assistant text should be rendered
                        # as a new assistant segment after the tool output rather than appended
                        # to the earlier pre-tool assistant message.
                        assistant_started = False
                        assistant_message_id = None
                        assistant_timestamp = None
                        tool_args = event["data"].get("args")
                        tool_name = event["data"].get("tool_name")
                        events.append(
                            build_event(
                                execution_id,
                                "tool_call_emitted",
                                tool=tool_name,
                                args=tool_args,
                            )
                        )
                    elif event["event"] == "tool_finished":
                        completed_tool_messages.append(
                            ToolMessage(
                                content=event["data"]["tool_output"],
                                tool_call_id=event["data"]["tool_call_id"],
                                name=event["data"]["tool_name"],
                                additional_kwargs={
                                    AGENTBOT_META_KEY: {
                                        "message_id": _new_prefixed_id("msg"),
                                        "timestamp": event["data"]["timestamp"],
                                    }
                                },
                            )
                        )
                        events.append(
                            build_event(
                                execution_id,
                                "tool_completed",
                                tool=event["data"]["tool_name"],
                                output=event["data"]["tool_output"],
                            )
                        )
                    yield event
                continue

            if event_type == "values" and isinstance(payload, dict):
                final_values = payload
    except Exception as exc:
        failure_event = build_event(
            execution_id,
            "run_failed",
            stage="graph_execution",
            error=str(exc),
        )
        events.append(failure_event)
        debug.log_event(failure_event)

        _persist_partial_failure(
            conversation_store=conversation_store,
            execution_store=execution_store,
            meta=meta,
            history=history,
            user_message=user_message,
            assistant_message_id=assistant_message_id,
            assistant_timestamp=assistant_timestamp,
            assistant_fragments=assistant_fragments,
            tool_messages=completed_tool_messages,
            events=events,
        )

        yield _ui_event("error", message=_format_graph_error(exc))
        yield _ui_event("done")
        return

    final_messages = final_values.get("messages") if isinstance(final_values, dict) else None
    if not isinstance(final_messages, list):
        events.append(
            build_event(
                execution_id,
                "run_failed",
                stage="stream_finalize",
                error="Streaming run did not produce a final message state.",
            )
        )
        _persist_partial_failure(
            conversation_store=conversation_store,
            execution_store=execution_store,
            meta=meta,
            history=history,
            user_message=user_message,
            assistant_message_id=assistant_message_id,
            assistant_timestamp=assistant_timestamp,
            assistant_fragments=assistant_fragments,
            tool_messages=completed_tool_messages,
            events=events,
        )
        yield _ui_event("error", message="Streaming run did not produce a final message state.")
        yield _ui_event("done")
        return

    final_assistant_message = _find_last_assistant_message(final_messages)
    final_text = _extract_assistant_content(final_assistant_message.content) if final_assistant_message else ""

    if final_assistant_message is not None:
        metadata = dict(getattr(final_assistant_message, "additional_kwargs", {}).get(AGENTBOT_META_KEY) or {})
        assistant_message_id = assistant_message_id or str(metadata.get("message_id") or _new_prefixed_id("msg"))
        assistant_timestamp = assistant_timestamp or str(metadata.get("timestamp") or _now_iso())
    elif assistant_started:
        assistant_message_id = assistant_message_id or _new_prefixed_id("msg")
        assistant_timestamp = assistant_timestamp or _now_iso()

    try:
        meta = conversation_store.replace_conversation_messages(
            meta.conversation_id,
            final_messages,
            existing_meta=meta,
        )
    except Exception as exc:
        failure_event = build_event(
            execution_id,
            "run_failed",
            stage="conversation_persistence",
            error=str(exc),
        )
        events.append(failure_event)
        debug.log_event(failure_event)
        try:
            execution_store.append_events(meta, events)
        except Exception:
            pass
        yield _ui_event("error", message=f"Failed to persist conversation history: {exc}")
        yield _ui_event("done")
        return

    if final_text:
        events.append(build_event(execution_id, "final_answer", content=final_text))

    try:
        execution_store.append_events(meta, events)
    except Exception as exc:
        yield _ui_event("error", message=f"Failed to persist execution log: {exc}")
        yield _ui_event("done")
        return

    if assistant_message_id and assistant_timestamp is not None:
        yield _ui_event(
            "assistant_completed",
            message_id=assistant_message_id,
            timestamp=assistant_timestamp,
            content=final_text,
        )

    yield _ui_event("conversation_committed", conversation_id=meta.conversation_id)
    yield _ui_event("done")


def _events_from_updates(
    payload: Any,
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
                for tool_call in message.tool_calls:
                    tool_call_id = str(tool_call.get("id") or _new_prefixed_id("call"))
                    if tool_call_id in emitted_tool_calls:
                        continue
                    emitted_tool_calls.add(tool_call_id)
                    yield _ui_event(
                        "tool_started",
                        tool_call_id=tool_call_id,
                        tool_name=str(tool_call.get("name") or "unknown_tool"),
                        args=tool_call.get("args") or {},
                        timestamp=_now_iso(),
                    )
            elif isinstance(message, ToolMessage):
                yield _ui_event(
                    "tool_finished",
                    tool_call_id=message.tool_call_id,
                    tool_name=message.name or "unknown_tool",
                    tool_output=_extract_assistant_content(message.content),
                    timestamp=_now_iso(),
                )


def _persist_partial_failure(
    *,
    conversation_store: ConversationStore,
    execution_store: ExecutionStore,
    meta,
    history: list[BaseMessage],
    user_message: HumanMessage,
    assistant_message_id: str | None,
    assistant_timestamp: str | None,
    assistant_fragments: list[str],
    tool_messages: list[ToolMessage],
    events: list[dict[str, Any]],
) -> None:
    persisted_messages: list[BaseMessage] = [*history, user_message]
    persisted_messages.extend(tool_messages)

    partial_assistant = "".join(assistant_fragments)
    if partial_assistant:
        persisted_messages.append(
            AIMessage(
                content=partial_assistant,
                additional_kwargs={
                    AGENTBOT_META_KEY: {
                        "message_id": assistant_message_id or _new_prefixed_id("msg"),
                        "timestamp": assistant_timestamp or _now_iso(),
                    }
                },
            )
        )

    try:
        updated_meta = conversation_store.replace_conversation_messages(
            meta.conversation_id,
            persisted_messages,
            existing_meta=meta,
        )
    except Exception:
        updated_meta = meta

    try:
        execution_store.append_events(updated_meta, events)
    except Exception:
        pass


def _find_last_assistant_message(messages: list[BaseMessage]) -> AIMessage | None:
    for message in reversed(messages):
        if isinstance(message, AIMessage) and _extract_assistant_content(message.content):
            return message
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            return message
    return None


def _extract_delta(payload: Any) -> str | None:
    if not isinstance(payload, tuple) or len(payload) != 2:
        return None

    token, _metadata = payload
    text = _extract_assistant_content(getattr(token, "content", token))
    return text if text else None


def _extract_assistant_content(content: Any) -> str:
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
    return {
        "event": event,
        "data": payload,
    }


def _normalize_stream_chunk(chunk: Any) -> tuple[str | None, Any]:
    if isinstance(chunk, tuple) and len(chunk) == 2 and isinstance(chunk[0], str):
        return chunk[0], chunk[1]

    if isinstance(chunk, dict):
        event_type = chunk.get("type")
        if isinstance(event_type, str):
            return event_type, chunk.get("data")

    return None, None


def _new_prefixed_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")
