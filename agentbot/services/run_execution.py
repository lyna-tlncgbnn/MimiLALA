"""Run execution use cases."""

from __future__ import annotations

from agentbot.app.runner import run_once
from agentbot.services.conversation_queries import ConversationQueries
from agentbot.services.run_queries import RunQueries


class RunExecution:
    """Execute synchronous run-oriented use cases."""

    def __init__(
        self,
        conversation_queries: ConversationQueries | None = None,
        run_queries: RunQueries | None = None,
    ):
        self.conversation_queries = conversation_queries or ConversationQueries()
        self.run_queries = run_queries or RunQueries()

    def send_message_to_conversation(self, conversation_id: str, user_text: str):
        reply = run_once(user_text, conversation_id=conversation_id)
        meta, messages = self.conversation_queries.get_conversation(conversation_id)
        return meta, messages, reply

    def send_run_to_conversation(self, conversation_id: str, user_text: str):
        reply = run_once(user_text, conversation_id=conversation_id)
        meta, messages = self.conversation_queries.get_conversation(conversation_id)
        run = self.run_queries.get_latest_for_conversation(conversation_id)
        return meta, run, messages, reply
