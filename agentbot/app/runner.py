"""Runner for single-turn CLI execution with local conversation and execution logs."""

from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from agentbot.app.debug import DebugPrinter
from agentbot.config.settings import Settings
from agentbot.graph.builder import build_graph
from agentbot.memory.conversation import ConversationStore
from agentbot.memory.execution import ExecutionStore, build_event, new_execution_id
from agentbot.models.llm import build_llm
from agentbot.prompts.system import get_system_prompt
from agentbot.tools.registry import get_registered_tools


class AgentBotError(RuntimeError):
    """User-facing runtime error."""


def run_once(user_text: str) -> str:
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

    conversation_store = ConversationStore()
    execution_store = ExecutionStore()
    tools = get_registered_tools()
    events: list[dict] = []

    try:
        meta, history = conversation_store.load_default_conversation()
    except Exception as exc:
        raise AgentBotError(f"Failed to load conversation history: {exc}") from exc

    if meta is None:
        meta = conversation_store.create_default_meta()

    execution_id = new_execution_id()
    events.append(
        build_event(
            execution_id,
            "conversation_loaded",
            message_count=len(history),
        )
    )
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
        raise AgentBotError(f"Failed to build graph: {exc}") from exc

    input_messages = [
        SystemMessage(content=get_system_prompt()),
        *history,
        HumanMessage(content=user_text),
    ]

    try:
        result = graph.invoke({"messages": input_messages})
    except Exception as exc:
        failure_event = build_event(
            execution_id,
            "run_failed",
            stage="graph_execution",
            error=str(exc),
        )
        events.append(failure_event)
        debug.log_event(failure_event)
        try:
            execution_store.append_default_events(meta, events)
        except Exception:
            pass
        raise AgentBotError(_format_graph_error(exc)) from exc

    new_messages = result["messages"][len(input_messages) :]
    message_events = _events_from_new_messages(new_messages, execution_id)
    events.extend(message_events)
    for event in message_events:
        debug.log_event(event)

    try:
        conversation_store.save_default_conversation(meta, result["messages"])
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
            execution_store.append_default_events(meta, events)
        except Exception:
            pass
        raise AgentBotError(f"Failed to persist conversation history: {exc}") from exc

    try:
        execution_store.append_default_events(meta, events)
    except Exception as exc:
        raise AgentBotError(f"Failed to persist execution log: {exc}") from exc

    return _extract_final_text(result["messages"])


def _extract_final_text(messages: list) -> str:
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            content = message.content
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
    raise AgentBotError("No assistant response was returned by the graph.")


def _format_graph_error(exc: Exception) -> str:
    message = str(exc)
    if message.startswith("Model execution failed:"):
        return message
    if message.startswith("Tool execution failed:"):
        return message
    return f"Graph execution failed: {message}"


def _events_from_new_messages(messages: list, execution_id: str) -> list[dict]:
    events: list[dict] = []
    for message in messages:
        if isinstance(message, AIMessage):
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    events.append(
                        build_event(
                            execution_id,
                            "tool_call_emitted",
                            tool=tool_call.get("name"),
                            args=tool_call.get("args"),
                        )
                    )
            else:
                events.append(
                    build_event(
                        execution_id,
                        "final_answer",
                        content=_stringify_message_content(message.content),
                    )
                )
        elif isinstance(message, ToolMessage):
            events.append(
                build_event(
                    execution_id,
                    "tool_completed",
                    tool=message.name or "unknown_tool",
                    output=_stringify_message_content(message.content),
                )
            )
    return events


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
