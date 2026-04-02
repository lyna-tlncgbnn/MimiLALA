"""Chat-oriented service helpers."""

from __future__ import annotations

from agentbot.app.runner import run_once
from agentbot.app.streaming_runner import stream_once
from agentbot.services.conversations import ConversationService
from agentbot.storage.db import AgentDatabase
from agentbot.storage.repositories import RunRepository


class ChatService:
    """Send user messages to a conversation and return the updated state."""

    def __init__(self, conversation_service: ConversationService | None = None):
        self.conversation_service = conversation_service or ConversationService()

    def send_message_to_conversation(self, conversation_id: str, user_text: str):
        reply = run_once(user_text, conversation_id=conversation_id)
        meta, messages = self.conversation_service.get_conversation(conversation_id)
        return meta, messages, reply

    def send_run_to_conversation(self, conversation_id: str, user_text: str):
        reply = run_once(user_text, conversation_id=conversation_id)
        meta, messages = self.conversation_service.get_conversation(conversation_id)

        database = AgentDatabase()
        database.initialize()
        with database.connect() as connection:
            run = RunRepository(connection).get_latest_for_conversation(conversation_id)
        if run is None:
            raise RuntimeError(f"No run persisted for conversation: {conversation_id}")
        return meta, run, messages, reply

    def stream_message_to_conversation(self, conversation_id: str, user_text: str):
        return stream_once(user_text, conversation_id=conversation_id)
