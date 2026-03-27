"""Runner for single-turn CLI execution with persisted short-term session history."""

from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from agentbot.config.settings import Settings
from agentbot.graph.builder import build_graph
from agentbot.memory.session import SessionStore
from agentbot.models.llm import build_llm
from agentbot.prompts.system import get_system_prompt


class AgentBotError(RuntimeError):
    """User-facing runtime error."""


def run_once(user_text: str) -> str:
    """Run a single LangGraph turn and return the assistant response."""
    try:
        settings = Settings.from_file()
    except ValueError as exc:
        raise AgentBotError(str(exc)) from exc

    try:
        llm = build_llm(settings)
    except Exception as exc:
        raise AgentBotError(f"Failed to initialize chat model: {exc}") from exc

    session_store = SessionStore()

    try:
        history = session_store.load_default_session()
        graph = build_graph(llm)
        result = graph.invoke(
            {
                "messages": [
                    SystemMessage(content=get_system_prompt()),
                    *history,
                    HumanMessage(content=user_text),
                ]
            }
        )
    except Exception as exc:
        raise AgentBotError(f"Graph execution failed: {exc}") from exc

    try:
        session_store.save_default_session(result["messages"])
    except ValueError as exc:
        raise AgentBotError(f"Failed to persist session history: {exc}") from exc

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
