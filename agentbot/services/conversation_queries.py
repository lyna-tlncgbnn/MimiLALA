"""Conversation query use cases."""

from __future__ import annotations

from agentbot.services.sqlite_conversations import SQLiteConversationService


class ConversationQueries:
    """Read conversation-oriented data through explicit query use cases."""

    def __init__(self, sqlite_service: SQLiteConversationService | None = None):
        self.sqlite_service = sqlite_service or SQLiteConversationService()

    def list_conversations(self):
        return self.sqlite_service.list_conversations()

    def get_conversation(self, conversation_id: str):
        return self.sqlite_service.get_conversation(conversation_id)

    def get_default_conversation(self):
        return self.sqlite_service.get_default_conversation()
