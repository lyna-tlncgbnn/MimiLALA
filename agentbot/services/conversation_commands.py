"""Conversation command use cases."""

from __future__ import annotations

from agentbot.services.sqlite_conversations import SQLiteConversationService


class ConversationCommands:
    """Write conversation-oriented changes through explicit command use cases."""

    def __init__(self, sqlite_service: SQLiteConversationService | None = None):
        self.sqlite_service = sqlite_service or SQLiteConversationService()

    def create_conversation(self, name: str | None = None):
        return self.sqlite_service.create_conversation(name)

    def rename_conversation(self, conversation_id: str, new_name: str):
        return self.sqlite_service.rename_conversation(conversation_id, new_name)

    def delete_conversation(self, conversation_id: str) -> None:
        self.sqlite_service.delete_conversation(conversation_id)
