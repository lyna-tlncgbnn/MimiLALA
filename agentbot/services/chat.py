"""Compatibility wrapper around run execution use cases."""

from __future__ import annotations

from agentbot.services.run_execution import RunExecution
from agentbot.services.run_streaming import RunStreaming


class ChatService:
    """Backward-compatible facade over explicit run execution use cases."""

    def __init__(
        self,
        run_execution: RunExecution | None = None,
        run_streaming: RunStreaming | None = None,
    ):
        self.run_execution = run_execution or RunExecution()
        self.run_streaming = run_streaming or RunStreaming()

    def send_message_to_conversation(self, conversation_id: str, user_text: str):
        return self.run_execution.send_message_to_conversation(conversation_id, user_text)

    def send_run_to_conversation(self, conversation_id: str, user_text: str):
        return self.run_execution.send_run_to_conversation(conversation_id, user_text)

    def stream_message_to_conversation(self, conversation_id: str, user_text: str):
        return self.run_streaming.stream_run_for_conversation(conversation_id, user_text)
