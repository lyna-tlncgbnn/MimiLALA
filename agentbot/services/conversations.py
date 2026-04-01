"""Conversation-oriented service helpers."""

from __future__ import annotations

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage

from agentbot.memory.conversation import (
    ASSISTANT_BROWSER_TASK_KEY,
    ASSISTANT_DELEGATION_KEY,
    ASSISTANT_METADATA_KEY,
    ASSISTANT_RESPONSE_KEY,
    ASSISTANT_STATE_KEY,
    ConversationMeta,
    ConversationStore,
)
from agentbot.memory.execution import ExecutionStore


class ConversationService:
    """High-level conversation operations for API consumers."""

    def __init__(
        self,
        conversation_store: ConversationStore | None = None,
        execution_store: ExecutionStore | None = None,
    ):
        self.conversation_store = conversation_store or ConversationStore()
        self.execution_store = execution_store or ExecutionStore()

    def list_conversations(self) -> list[ConversationMeta]:
        self.conversation_store.ensure_default_conversation()
        return self.conversation_store.list_conversations()

    def create_conversation(self, name: str | None = None) -> ConversationMeta:
        return self.conversation_store.create_conversation(name)

    def get_conversation(self, conversation_id: str) -> tuple[ConversationMeta, list[BaseMessage]]:
        return self.conversation_store.get_conversation(conversation_id)

    def rename_conversation(self, conversation_id: str, new_name: str) -> ConversationMeta:
        return self.conversation_store.rename_conversation(conversation_id, new_name)

    def delete_conversation(self, conversation_id: str) -> None:
        self.conversation_store.delete_conversation(conversation_id)
        self.execution_store.delete_execution_file(conversation_id)

    def get_default_conversation(self) -> tuple[ConversationMeta, list[BaseMessage]]:
        return self.conversation_store.load_default_conversation()


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
        additional_kwargs = getattr(message, "additional_kwargs", {})
        response = additional_kwargs.get(ASSISTANT_RESPONSE_KEY)
        if response is not None:
            payload["response"] = response
        delegation = additional_kwargs.get(ASSISTANT_DELEGATION_KEY)
        if delegation is not None:
            payload["delegation"] = delegation
        browser_task = additional_kwargs.get(ASSISTANT_BROWSER_TASK_KEY)
        if browser_task is not None:
            payload["browser_task"] = browser_task
        state = additional_kwargs.get(ASSISTANT_STATE_KEY)
        if state is not None:
            payload["state"] = state
        message_metadata = additional_kwargs.get(ASSISTANT_METADATA_KEY)
        if message_metadata is not None:
            payload["metadata"] = message_metadata

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
