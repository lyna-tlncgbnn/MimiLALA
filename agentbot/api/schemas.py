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
    run_id: str | None = None
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


class RunSummary(BaseModel):
    run_id: str
    conversation_id: str
    thread_id: str
    status: str
    started_at: str
    ended_at: str | None = None
    workflow_name: str | None = None
    user_message_id: str | None = None
    final_message_id: str | None = None
    error_message: str | None = None
    step_count: int = 0
    visible_step_count: int = 0
    has_execution: bool = False


class RunStepPayload(BaseModel):
    step_id: str
    run_id: str
    parent_step_id: str | None = None
    step_type: str
    title: str
    status: str
    display_mode: str
    sort_order: int
    started_at: str
    ended_at: str | None = None
    tool_name: str | None = None
    tool_call_id: str | None = None
    input_json: str | None = None
    output_json: str | None = None
    summary_text: str | None = None


class RunDetail(BaseModel):
    run: RunSummary


class RunStepsDetail(BaseModel):
    run: RunSummary
    steps: list[RunStepPayload]


class ConversationRunsDetail(BaseModel):
    conversation: ConversationSummary
    runs: list[RunSummary]


class SendRunResponse(BaseModel):
    conversation: ConversationSummary
    run: RunSummary
    messages: list[MessagePayload]
    reply: MessagePayload
