"""Compatibility helpers for conversation use cases and API serialization."""

from __future__ import annotations

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage

from agentbot.services.conversation_commands import ConversationCommands
from agentbot.services.conversation_queries import ConversationQueries


class ConversationService:
    """Backward-compatible facade over explicit conversation use cases."""

    def __init__(
        self,
        queries: ConversationQueries | None = None,
        commands: ConversationCommands | None = None,
    ):
        self.queries = queries or ConversationQueries()
        self.commands = commands or ConversationCommands()

    def list_conversations(self):
        return self.queries.list_conversations()

    def create_conversation(self, name: str | None = None):
        return self.commands.create_conversation(name)

    def get_conversation(self, conversation_id: str):
        return self.queries.get_conversation(conversation_id)

    def rename_conversation(self, conversation_id: str, new_name: str):
        return self.commands.rename_conversation(conversation_id, new_name)

    def delete_conversation(self, conversation_id: str) -> None:
        self.commands.delete_conversation(conversation_id)

    def get_default_conversation(self):
        return self.queries.get_default_conversation()


def message_to_api_dict(message: BaseMessage) -> dict:
    """Convert a LangChain message into a frontend-safe payload."""
    metadata = dict(getattr(message, "additional_kwargs", {}).get("_agentbot") or {})
    role = "assistant"
    payload: dict = {
        "message_id": metadata.get("message_id"),
        "timestamp": metadata.get("timestamp"),
        "content": _stringify_message_content(message.content),
        "role": role,
    }

    if isinstance(message, HumanMessage):
        payload["role"] = "user"
    elif isinstance(message, ToolMessage):
        payload["role"] = "tool"
        payload["tool_call_id"] = message.tool_call_id
    elif isinstance(message, AIMessage):
        payload["role"] = "assistant"
        if message.tool_calls:
            payload["tool_calls"] = message.tool_calls

    if getattr(message, "name", None):
        payload["name"] = message.name

    return payload


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
