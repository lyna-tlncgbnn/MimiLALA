"""SQLite-backed conversation and transcript services."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from agentbot.storage.common import now_iso
from agentbot.storage.db import AgentDatabase
from agentbot.storage.models import ConversationRow, MessageRow
from agentbot.storage.repositories import ConversationRepository, MessageRepository

DEFAULT_CONVERSATION_TITLE = "default"


@dataclass(slots=True)
class TranscriptMessage:
    message_id: str
    role: str
    content: str
    created_at: str
    run_id: str | None = None
    phase: str | None = None
    visibility: str | None = None


class SQLiteConversationService:
    """Primary conversation service backed by SQLite."""

    def __init__(self, database: AgentDatabase | None = None):
        self.database = database or AgentDatabase()

    def list_conversations(self) -> list[ConversationRow]:
        self.database.initialize()
        with self.database.connect() as connection:
            repo = ConversationRepository(connection)
            return repo.list_all()

    def create_conversation(self, title: str | None = None) -> ConversationRow:
        self.database.initialize()
        with self.database.connect() as connection:
            repo = ConversationRepository(connection)
            return repo.create((title or "").strip() or _default_generated_title())

    def get_conversation(self, conversation_id: str) -> tuple[ConversationRow, list[TranscriptMessage]]:
        self.database.initialize()
        with self.database.connect() as connection:
            conversation_repo = ConversationRepository(connection)
            message_repo = MessageRepository(connection)
            conversation = conversation_repo.get(conversation_id)
            if conversation is None:
                raise FileNotFoundError(f"Conversation not found: {conversation_id}")
            messages = [transcript_message_from_row(row) for row in message_repo.list_for_conversation(conversation_id)]
            return conversation, messages

    def rename_conversation(self, conversation_id: str, title: str) -> ConversationRow:
        self.database.initialize()
        with self.database.connect() as connection:
            repo = ConversationRepository(connection)
            updated = repo.update_title(conversation_id, title)
            if updated is None:
                raise FileNotFoundError(f"Conversation not found: {conversation_id}")
            return updated

    def delete_conversation(self, conversation_id: str) -> None:
        self.database.initialize()
        with self.database.connect() as connection:
            conversation_repo = ConversationRepository(connection)
            conversation = conversation_repo.get(conversation_id)
            if conversation is None:
                raise FileNotFoundError(f"Conversation not found: {conversation_id}")
        from agentbot.storage.shadow_runtime import RuntimeShadowWriter

        RuntimeShadowWriter(self.database).delete_conversation(conversation_id)

    def get_default_conversation(self) -> tuple[ConversationRow, list[TranscriptMessage]]:
        self.database.initialize()
        with self.database.connect() as connection:
            conversation_repo = ConversationRepository(connection)
            conversations = conversation_repo.list_all()
            if conversations:
                latest = conversations[0]
                message_repo = MessageRepository(connection)
                return latest, [transcript_message_from_row(row) for row in message_repo.list_for_conversation(latest.conversation_id)]

            created = conversation_repo.create(DEFAULT_CONVERSATION_TITLE)
            return created, []

    def get_conversation_history_messages(self, conversation_id: str) -> list[BaseMessage]:
        _conversation, transcript = self.get_conversation(conversation_id)
        return [transcript_message_to_langchain(message) for message in transcript]


def transcript_message_from_row(row: MessageRow) -> TranscriptMessage:
    return TranscriptMessage(
        message_id=row.message_id,
        role=row.role,
        content=_stringify_content_json(row.content_json),
        created_at=row.created_at,
        run_id=row.run_id,
        phase=row.phase,
        visibility=row.visibility,
    )


def transcript_message_to_langchain(message: TranscriptMessage) -> BaseMessage:
    additional_kwargs = {
        "_agentbot": {
            "message_id": message.message_id,
            "timestamp": message.created_at,
        }
    }
    if message.role == "user":
        return HumanMessage(content=message.content, additional_kwargs=additional_kwargs)
    if message.role == "assistant":
        return AIMessage(content=message.content, additional_kwargs=additional_kwargs)
    raise ValueError(f"Unsupported transcript role: {message.role!r}")


def _stringify_content_json(content_json: str) -> str:
    try:
        payload = json.loads(content_json)
    except json.JSONDecodeError:
        return content_json

    if isinstance(payload, str):
        return payload
    if isinstance(payload, list):
        parts: list[str] = []
        for item in payload:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
        return "\n".join(part for part in parts if part).strip()
    if isinstance(payload, dict) and payload.get("type") == "text":
        return str(payload.get("text", ""))
    return str(payload)


def _default_generated_title() -> str:
    return f"Conversation {now_iso()}"
