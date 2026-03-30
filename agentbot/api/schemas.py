"""Pydantic schemas for the local API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ConversationSummary(BaseModel):
    conversation_id: str
    name: str
    created_at: str
    updated_at: str


class MessagePayload(BaseModel):
    message_id: str | None = None
    timestamp: str | None = None
    role: str
    content: str
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[dict] | None = None


class ConversationDetail(BaseModel):
    conversation: ConversationSummary
    messages: list[MessagePayload]


class CreateConversationRequest(BaseModel):
    name: str | None = None


class RenameConversationRequest(BaseModel):
    name: str = Field(min_length=1)


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1)


class SendMessageResponse(BaseModel):
    conversation: ConversationSummary
    messages: list[MessagePayload]
    reply: MessagePayload
