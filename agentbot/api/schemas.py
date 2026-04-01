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
    response: dict | None = None
    delegation: dict | None = None
    browser_task: dict | None = None
    state: dict | None = None
    metadata: dict | None = None


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


class BrowserStepPayload(BaseModel):
    step_number: int
    action: dict
    result: dict | None = None


class BrowserTaskRequest(BaseModel):
    task: str = Field(min_length=1)
    start_url: str | None = None
    max_steps: int = Field(default=5, ge=1, le=12)


class BrowserTaskResponse(BaseModel):
    status: str
    final_response: str | None = None
    error_message: str | None = None
    current_url: str | None = None
    page_title: str | None = None
    step_count: int
    steps: list[BrowserStepPayload]
