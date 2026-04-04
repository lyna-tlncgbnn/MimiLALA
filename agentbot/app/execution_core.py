"""Shared execution helpers for sync and streaming run adapters."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterator
from uuid import uuid4

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from agentbot.config.settings import Settings
from agentbot.graph.builder import build_graph
from agentbot.graph.checkpoints import sqlite_checkpointer, thread_config
from agentbot.models.llm import build_llm
from agentbot.prompts.system import get_system_prompt
from agentbot.services.sqlite_conversations import SQLiteConversationService
from agentbot.storage.common import AGENTBOT_META_KEY
from agentbot.storage.shadow_runtime import ActiveRunShadow, RuntimeShadowWriter


class ExecutionSetupError(RuntimeError):
    """Raised when a run cannot be initialized."""


@dataclass(slots=True)
class PreparedRun:
    settings: Settings
    llm: Any
    conversation_service: SQLiteConversationService
    runtime_writer: RuntimeShadowWriter
    meta: Any
    user_message: HumanMessage
    active_run: ActiveRunShadow | None
    thread_id: str
    user_message_id: str
    user_timestamp: str


def prepare_run(
    user_text: str,
    *,
    conversation_id: str | None,
    streaming: bool,
    require_persisted_run: bool,
) -> PreparedRun:
    try:
        settings = Settings.from_file()
    except ValueError as exc:
        raise ExecutionSetupError(str(exc)) from exc

    try:
        llm = build_llm(settings, streaming=streaming)
    except Exception as exc:
        raise ExecutionSetupError(f"Failed to initialize chat model: {exc}") from exc

    conversation_service = SQLiteConversationService()
    runtime_writer = RuntimeShadowWriter()

    try:
        meta = load_target_conversation(conversation_service, conversation_id)
    except Exception as exc:
        raise ExecutionSetupError(f"Failed to load conversation history: {exc}") from exc

    user_message_id = new_prefixed_id("msg")
    user_timestamp = now_iso()
    user_message = HumanMessage(
        content=user_text,
        additional_kwargs={
            AGENTBOT_META_KEY: {
                "message_id": user_message_id,
                "timestamp": user_timestamp,
            }
        },
    )
    active_run = safe_start_run(runtime_writer, meta=meta, user_message=user_message)
    if require_persisted_run and active_run is None:
        raise ExecutionSetupError("Failed to start run persistence.")

    thread_id = active_run.run_id if active_run is not None else new_prefixed_id("run")
    return PreparedRun(
        settings=settings,
        llm=llm,
        conversation_service=conversation_service,
        runtime_writer=runtime_writer,
        meta=meta,
        user_message=user_message,
        active_run=active_run,
        thread_id=thread_id,
        user_message_id=user_message_id,
        user_timestamp=user_timestamp,
    )


def load_target_conversation(
    conversation_service: SQLiteConversationService,
    conversation_id: str | None,
):
    if conversation_id:
        meta, _messages = conversation_service.get_conversation(conversation_id)
        return meta
    meta, _messages = conversation_service.get_default_conversation()
    return meta


def build_input_messages(
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


def execute_graph(prepared: PreparedRun, *, stream_mode: list[str]) -> Iterator[tuple[str | None, Any]]:
    with sqlite_checkpointer() as checkpointer:
        input_messages = build_input_messages(
            conversation_service=prepared.conversation_service,
            conversation_id=prepared.meta.conversation_id,
            user_message=prepared.user_message,
            seed_from_transcript=True,
        )
        graph = build_graph(prepared.llm, checkpointer=checkpointer)
        for chunk in graph.stream(
            {"messages": input_messages},
            config=thread_config(prepared.thread_id),
            stream_mode=stream_mode,
            version="v2",
        ):
            yield normalize_stream_chunk(chunk)


def find_final_assistant_message(messages: list[BaseMessage]) -> AIMessage | None:
    for message in reversed(messages):
        if isinstance(message, AIMessage) and stringify_message_content(message.content):
            return message
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            return message
    return None


def extract_final_text(messages: list[BaseMessage]) -> str:
    final_assistant = find_final_assistant_message(messages)
    if final_assistant is None:
        raise RuntimeError("No assistant response was returned by the graph.")
    return stringify_message_content(final_assistant.content)


def persist_run_outcome(
    *,
    runtime_writer: RuntimeShadowWriter,
    active_run: ActiveRunShadow,
    meta: Any,
    final_messages: list[BaseMessage],
) -> None:
    final_assistant = find_final_assistant_message(final_messages)
    if final_assistant is None:
        runtime_writer.fail_run(
            active_run,
            meta=meta,
            error_message="No final assistant message was produced.",
            ended_at=now_iso(),
        )
        return

    assistant_metadata = message_metadata(final_assistant)
    runtime_writer.complete_run(
        active_run,
        meta=meta,
        assistant_message_id=assistant_metadata["message_id"],
        assistant_text=stringify_message_content(final_assistant.content),
        assistant_timestamp=assistant_metadata["timestamp"],
    )


def format_graph_error(exc: Exception) -> str:
    message = str(exc)
    if message.startswith("Model execution failed:"):
        return message
    if message.startswith("Tool execution failed:"):
        return message
    return f"Graph execution failed: {message}"


def normalize_stream_chunk(chunk: Any) -> tuple[str | None, Any]:
    if isinstance(chunk, tuple) and len(chunk) == 2 and isinstance(chunk[0], str):
        return chunk[0], chunk[1]
    if isinstance(chunk, dict):
        event_type = chunk.get("type")
        if isinstance(event_type, str):
            return event_type, chunk.get("data")
    return None, None


def extract_delta(payload: Any) -> str | None:
    if not isinstance(payload, tuple) or len(payload) != 2:
        return None
    token, metadata = payload
    if not isinstance(metadata, dict):
        return None
    if metadata.get("langgraph_node") not in {"chatbot", "browser_summary"}:
        return None
    text = stringify_inline_content(getattr(token, "content", token))
    return text if text else None


def stringify_message_content(content: Any) -> str:
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
    return str(content) if content is not None else ""


def stringify_inline_content(content: Any) -> str:
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


def message_metadata(message: BaseMessage) -> dict[str, str]:
    metadata = dict(getattr(message, "additional_kwargs", {}).get(AGENTBOT_META_KEY) or {})
    return {
        "message_id": str(metadata.get("message_id") or new_prefixed_id("msg")),
        "timestamp": str(metadata.get("timestamp") or now_iso()),
    }


def safe_start_run(
    runtime_writer: RuntimeShadowWriter,
    *,
    meta: Any,
    user_message: HumanMessage,
) -> ActiveRunShadow | None:
    try:
        metadata = message_metadata(user_message)
        return runtime_writer.start_run(
            meta=meta,
            user_message_id=metadata["message_id"],
            user_text=stringify_message_content(user_message.content),
            user_timestamp=metadata["timestamp"],
        )
    except Exception:
        return None


def new_prefixed_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def best_effort(action) -> None:
    try:
        action()
    except Exception:
        pass
