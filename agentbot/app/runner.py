"""Runner for single-turn execution backed by SQLite transcript and run storage."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from agentbot.app.graph_runtime_events import apply_runtime_events_from_updates
from agentbot.app.debug import DebugPrinter
from agentbot.config.settings import Settings
from agentbot.graph.builder import build_graph
from agentbot.graph.checkpoints import sqlite_checkpointer, thread_config
from agentbot.models.llm import build_llm
from agentbot.prompts.system import get_system_prompt
from agentbot.services.sqlite_conversations import SQLiteConversationService
from agentbot.storage.common import AGENTBOT_META_KEY
from agentbot.storage.shadow_runtime import ActiveRunShadow, RuntimeShadowWriter
from agentbot.tools.infra.error_handling import is_tool_error_output
from agentbot.tools.registry import get_registered_tools


class AgentBotError(RuntimeError):
    """User-facing runtime error."""


def run_once(user_text: str, conversation_id: str | None = None) -> str:
    """Run a single LangGraph turn and return the assistant response."""
    try:
        settings = Settings.from_file()
    except ValueError as exc:
        raise AgentBotError(str(exc)) from exc

    debug = DebugPrinter(enabled=settings.debug)

    try:
        llm = build_llm(settings)
    except Exception as exc:
        raise AgentBotError(f"Failed to initialize chat model: {exc}") from exc

    conversation_service = SQLiteConversationService()
    runtime_writer = RuntimeShadowWriter()
    tools = get_registered_tools()

    try:
        meta = _load_target_conversation(conversation_service, conversation_id)
    except Exception as exc:
        raise AgentBotError(f"Failed to load conversation history: {exc}") from exc

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
    thread_id = active_run.run_id if active_run is not None else _new_prefixed_id("run")

    debug.log(f"tools registered: {', '.join(tool.name for tool in tools)}")
    debug.log("graph execution started")

    try:
        with sqlite_checkpointer() as checkpointer:
            input_messages = _build_input_messages(
                conversation_service=conversation_service,
                conversation_id=meta.conversation_id,
                user_message=user_message,
                seed_from_transcript=True,
            )
            graph = build_graph(llm, checkpointer=checkpointer)
            debug.log("loaded conversation state: transcript seed (per-run thread)")
            emitted_tool_calls: set[str] = set()
            final_values: dict | None = None
            for chunk in graph.stream(
                {"messages": input_messages},
                config=thread_config(thread_id),
                stream_mode=["updates", "values"],
                version="v2",
            ):
                event_type, payload = _normalize_stream_chunk(chunk)
                if event_type == "updates" and active_run is not None:
                    active_run, _runtime_events = apply_runtime_events_from_updates(
                        payload,
                        active_run,
                        runtime_writer,
                        emitted_tool_calls,
                    )
                elif event_type == "values" and isinstance(payload, dict):
                    final_values = payload
            result = final_values or {}
    except Exception as exc:
        if active_run is not None:
            _best_effort(
                lambda: runtime_writer.fail_run(
                    active_run,
                    meta=meta,
                    error_message=_format_graph_error(exc),
                    ended_at=_now_iso(),
                )
            )
        raise AgentBotError(_format_graph_error(exc)) from exc

    final_messages = result["messages"]
    if active_run is not None:
        _best_effort(
            lambda: _persist_run_outcome(
                runtime_writer=runtime_writer,
                active_run=active_run,
                meta=meta,
                final_messages=final_messages,
            )
        )

    return _extract_final_text(final_messages)


def _load_target_conversation(
    conversation_service: SQLiteConversationService,
    conversation_id: str | None,
):
    if conversation_id:
        meta, _messages = conversation_service.get_conversation(conversation_id)
        return meta
    meta, _messages = conversation_service.get_default_conversation()
    return meta


def _build_input_messages(
    *,
    conversation_service: SQLiteConversationService,
    conversation_id: str,
    user_message: HumanMessage,
    seed_from_transcript: bool,
) -> list:
    if not seed_from_transcript:
        return [user_message]
    history = conversation_service.get_conversation_history_messages(conversation_id)
    return [
        SystemMessage(content=get_system_prompt()),
        *history,
        user_message,
    ]


def _messages_for_current_run(messages: list, user_message_id: str) -> list:
    for index, message in enumerate(messages):
        metadata = _message_metadata(message)
        if metadata["message_id"] == user_message_id:
            return messages[index + 1 :]
    return messages


def _extract_final_text(messages: list) -> str:
    final_assistant = _find_final_assistant_message(messages)
    if final_assistant is None:
        raise AgentBotError("No assistant response was returned by the graph.")
    return _stringify_message_content(final_assistant.content)


def _format_graph_error(exc: Exception) -> str:
    message = str(exc)
    if message.startswith("Model execution failed:"):
        return message
    if message.startswith("Tool execution failed:"):
        return message
    return f"Graph execution failed: {message}"


def _normalize_stream_chunk(chunk):
    if isinstance(chunk, tuple) and len(chunk) == 2 and isinstance(chunk[0], str):
        return chunk[0], chunk[1]
    if isinstance(chunk, dict):
        event_type = chunk.get("type")
        if isinstance(event_type, str):
            return event_type, chunk.get("data")
    return None, None


def _persist_run_outcome(
    *,
    runtime_writer: RuntimeShadowWriter,
    active_run: ActiveRunShadow,
    meta,
    final_messages: list,
) -> None:
    final_assistant = _find_final_assistant_message(final_messages)
    if final_assistant is None:
        runtime_writer.fail_run(
            active_run,
            meta=meta,
            error_message="No final assistant message was produced.",
            ended_at=_now_iso(),
        )
        return

    assistant_metadata = _message_metadata(final_assistant)
    runtime_writer.complete_run(
        active_run,
        meta=meta,
        assistant_message_id=assistant_metadata["message_id"],
        assistant_text=_stringify_message_content(final_assistant.content),
        assistant_timestamp=assistant_metadata["timestamp"],
    )


def _find_final_assistant_message(messages: list) -> AIMessage | None:
    for message in reversed(messages):
        if isinstance(message, AIMessage) and _stringify_message_content(message.content):
            return message
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            return message
    return None


def _stringify_message_content(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_chunks: list[str] = []
        for item in content:
            if isinstance(item, str):
                text_chunks.append(item)
            elif isinstance(item, dict) and item.get("type") == "text":
                text_chunks.append(str(item.get("text", "")))
        return "\n".join(chunk for chunk in text_chunks if chunk).strip()
    return str(content)


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


def _message_metadata(message) -> dict[str, str]:
    metadata = dict(getattr(message, "additional_kwargs", {}).get(AGENTBOT_META_KEY) or {})
    return {
        "message_id": str(metadata.get("message_id") or _new_prefixed_id("msg")),
        "timestamp": str(metadata.get("timestamp") or _now_iso()),
    }


def _new_prefixed_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _best_effort(action) -> None:
    try:
        action()
    except Exception:
        pass
