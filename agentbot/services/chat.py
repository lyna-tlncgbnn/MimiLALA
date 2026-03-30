"""Chat-oriented service helpers."""

from __future__ import annotations

from agentbot.app.runner import run_once
from agentbot.services.conversations import ConversationService


class ChatService:
    """Send user messages to a conversation and return the updated state."""

    def __init__(self, conversation_service: ConversationService | None = None):
        self.conversation_service = conversation_service or ConversationService()

    def send_message_to_conversation(self, conversation_id: str, user_text: str):
        reply = run_once(user_text, conversation_id=conversation_id)
        meta, messages = self.conversation_service.get_conversation(conversation_id)
        return meta, messages, reply
