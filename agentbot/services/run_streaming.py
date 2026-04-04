"""Streaming run use cases."""

from __future__ import annotations

from agentbot.app.streaming_runner import stream_once


class RunStreaming:
    """Execute streaming run-oriented use cases."""

    def stream_run_for_conversation(self, conversation_id: str, user_text: str):
        return stream_once(user_text, conversation_id=conversation_id)
