"""Serialization helpers for API responses."""

from __future__ import annotations

from agentbot.memory.conversation import ConversationMeta
from agentbot.services.conversations import message_to_api_dict


def serialize_conversation_meta(meta: ConversationMeta) -> dict:
    return {
        "conversation_id": meta.conversation_id,
        "name": meta.name,
        "created_at": meta.created_at,
        "updated_at": meta.updated_at,
    }


def serialize_messages(messages: list) -> list[dict]:
    return [message_to_api_dict(message) for message in messages]
